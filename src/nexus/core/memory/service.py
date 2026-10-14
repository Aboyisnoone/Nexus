from typing import List, Optional, Tuple
import uuid
from datetime import datetime

from nexus.core.persistence.repository import NexusRepository
from nexus.core.domain.memory import (
    MemoryItem, MemoryState, MemoryUpdate, MemoryUpdateType,
    Evidence, ConfirmationEvent, Contradiction
)

class MemoryTransitionError(Exception):
    pass

class MemoryService:
    def __init__(self, repo: NexusRepository):
        self.repo = repo

    def retrieve(
        self, 
        context_id: str, 
        key: Optional[str] = None, 
        state: Optional[MemoryState] = None
    ) -> List[MemoryItem]:
        '''
        Deterministic structured retrieval.
        Returns active (latest version) memories for the given context.
        Orders deterministically by context_id, key, version, id.
        '''
        all_memories = self.repo.load_memories(context_id)
        
        # Filter active versions (memories that are not superseded by a newer version)
        # We can determine the latest version by finding the max version per context_id + key,
        # or by checking which memories have no other memory pointing to them via previous_version_id.
        # Actually, if a memory is updated, we keep the same key. There could be multiple distinct memories for the same key.
        # So we group by id chain. A memory is latest if no other memory has previous_version_id == its id.
        superseded_ids = {m.previous_version_id for m in all_memories if m.previous_version_id}
        active_memories = [m for m in all_memories if m.id not in superseded_ids]
        
        if key:
            active_memories = [m for m in active_memories if m.key == key]
        if state:
            active_memories = [m for m in active_memories if m.state == state]
            
        # Deterministic sort
        active_memories.sort(key=lambda m: (m.context_id, m.key, m.version, m.id))
        return active_memories

    def apply_post_run_updates(self, updates: List[MemoryUpdate]):
        '''
        Applies a batch of memory updates post-run.
        Memory mutation must be explicit and deterministic.
        '''
        for update in updates:
            self._apply_single_update(update)

    def _apply_single_update(self, update: MemoryUpdate):
        if update.update_type in (MemoryUpdateType.OBSERVE, MemoryUpdateType.INFER):
            self._handle_observation_or_inference(update)
        elif update.update_type == MemoryUpdateType.CONFIRM:
            self._handle_confirmation(update)
        elif update.update_type == MemoryUpdateType.RECORD_CONTRADICTION:
            self._handle_contradiction(update)
        else:
            raise ValueError(f"Unknown update type: {update.update_type}")

    def _handle_observation_or_inference(self, update: MemoryUpdate):
        target_state = MemoryState.OBSERVED if update.update_type == MemoryUpdateType.OBSERVE else MemoryState.INFERRED
        
        if not update.memory_id:
            # Create new memory
            new_mem = MemoryItem(
                id=str(uuid.uuid4()),
                context_id=update.context_id,
                key=update.key,
                value=update.value,
                state=target_state,
                simulated_time=update.simulated_time,
                evidence=(update.evidence,)
            )
            self.repo.save_memory(new_mem)
            return

        # Update existing memory
        existing = self._get_existing_active(update.context_id, update.memory_id)
        
        # State machine transition rules
        if existing.state == MemoryState.CONFIRMED:
            raise MemoryTransitionError("Cannot demote CONFIRMED memory via OBSERVE or INFER. Use RECORD_CONTRADICTION.")
        if existing.state == MemoryState.INFERRED and target_state == MemoryState.OBSERVED:
             # Can append evidence, but doesn't demote state
             target_state = MemoryState.INFERRED
             
        # Create new version
        new_evidence = tuple(list(existing.evidence) + [update.evidence])
        
        new_mem = existing.model_copy(update={
            "id": str(uuid.uuid4()),
            "state": target_state,
            "value": update.value,
            "simulated_time": update.simulated_time,
            "evidence": new_evidence,
            "version": existing.version + 1,
            "previous_version_id": existing.id
        })
        self.repo.save_memory(new_mem)

    def _handle_confirmation(self, update: MemoryUpdate):
        if not update.memory_id:
            # Create fresh confirmed memory (e.g. user directly stated preference)
            conf_event = ConfirmationEvent(
                memory_id="pending", # will fix below
                context_id=update.context_id,
                source=update.source or "Unknown",
                simulated_time=update.simulated_time,
                evidence=update.evidence
            )
            new_id = str(uuid.uuid4())
            conf_event = conf_event.model_copy(update={"memory_id": new_id})
            
            new_mem = MemoryItem(
                id=new_id,
                context_id=update.context_id,
                key=update.key,
                value=update.value,
                state=MemoryState.CONFIRMED,
                simulated_time=update.simulated_time,
                evidence=(update.evidence,),
                confirmation_event=conf_event
            )
            self.repo.save_memory(new_mem)
            return
            
        existing = self._get_existing_active(update.context_id, update.memory_id)
        if existing.state == MemoryState.CONFIRMED:
            return # Already confirmed
            
        conf_event = ConfirmationEvent(
            memory_id=existing.id,
            context_id=existing.context_id,
            source=update.source or "Unknown",
            simulated_time=update.simulated_time,
            evidence=update.evidence
        )
        
        new_evidence = tuple(list(existing.evidence) + [update.evidence])
        
        new_mem = existing.model_copy(update={
            "id": str(uuid.uuid4()),
            "state": MemoryState.CONFIRMED,
            "value": update.value,
            "simulated_time": update.simulated_time,
            "evidence": new_evidence,
            "version": existing.version + 1,
            "previous_version_id": existing.id,
            "confirmation_event": conf_event
        })
        self.repo.save_memory(new_mem)

    def _handle_contradiction(self, update: MemoryUpdate):
        if not update.memory_id:
            raise ValueError("Contradiction must target an existing memory_id")
            
        existing = self._get_existing_active(update.context_id, update.memory_id)
        
        contradiction = Contradiction(
            observation_evidence=update.evidence,
            simulated_time=update.simulated_time,
            detail=update.detail or "Contradicting observation"
        )
        
        new_contradictions = tuple(list(existing.contradictions) + [contradiction])
        
        new_mem = existing.model_copy(update={
            "id": str(uuid.uuid4()),
            "simulated_time": update.simulated_time,
            "version": existing.version + 1,
            "previous_version_id": existing.id,
            "contradictions": new_contradictions
        })
        # State and value remain unchanged! Confirmation wins.
        self.repo.save_memory(new_mem)

    def _get_existing_active(self, context_id: str, memory_id: str) -> MemoryItem:
        memories = self.retrieve(context_id)
        for m in memories:
            if m.id == memory_id or memory_id in self._get_history_chain(m.id, context_id):
                return m
        # If not active, maybe they passed an old ID? Try to find it and traverse forward.
        all_mems = self.repo.load_memories(context_id)
        by_prev = {m.previous_version_id: m for m in all_mems if m.previous_version_id}
        
        current_id = memory_id
        while current_id in by_prev:
            current_id = by_prev[current_id].id
            
        final_mem = next((m for m in all_mems if m.id == current_id), None)
        if not final_mem:
             raise ValueError(f"Memory {memory_id} not found in context {context_id}")
        return final_mem

    def _get_history_chain(self, latest_id: str, context_id: str) -> List[str]:
        all_mems = {m.id: m for m in self.repo.load_memories(context_id)}
        chain = []
        curr = all_mems.get(latest_id)
        while curr and curr.previous_version_id:
            chain.append(curr.previous_version_id)
            curr = all_mems.get(curr.previous_version_id)
        return chain
