export interface ScenarioManifest {
    id: string;
    label: string;
    description: string;
}

export const SCENARIOS: ScenarioManifest[] = [
    { id: "core_01_happy_path", label: "Core 01: Happy Path", description: "A straightforward scheduling request." },
    { id: "core_02_hard_conflict", label: "Core 02: Hard Conflict", description: "Direct calendar overlap requiring rejection." },
    { id: "core_03_privacy_conflict", label: "Core 03: Privacy Conflict", description: "Conflict where private details must be scrubbed." },
    { id: "core_04_soft_preference", label: "Core 04: Soft Preference", description: "Select between options based on preferences." },
    { id: "core_05_explicit_override", label: "Core 05: Explicit Override", description: "VIP overrides flexible calendar event." },
    { id: "core_06_timezone_conflict", label: "Core 06: Timezone Conflict", description: "Coordinate across timezones." },
    { id: "core_07_dst_edge_case", label: "Core 07: DST Edge Case", description: "Cross daylight saving time boundary." },
    { id: "core_08_stale_memory", label: "Core 08: Stale Memory", description: "Ignore old memory when superseded." },
    { id: "core_09_privacy_paraphrase", label: "Core 09: Privacy Paraphrase", description: "Abstract private details into safe terms." },
    { id: "core_10_no_perfect_option", label: "Core 10: No Perfect Option", description: "Propose partial availability when necessary." }
];
