from typing import Literal, Union, Tuple, Annotated
from pydantic import Field
from .base import FrozenBaseModel

class BaseAssertion(FrozenBaseModel):
    pass

class ActionTypeEquals(BaseAssertion):
    type: Literal["action_type_equals"] = "action_type_equals"
    expected: str

class SelectedOptionEquals(BaseAssertion):
    type: Literal["selected_option_equals"] = "selected_option_equals"
    expected: str

class RankedOptionsEquals(BaseAssertion):
    type: Literal["ranked_options_equals"] = "ranked_options_equals"
    expected: Tuple[str, ...]

class PublicReasonEquals(BaseAssertion):
    type: Literal["public_reason_equals"] = "public_reason_equals"
    expected: str

class CommunicationTemplateEquals(BaseAssertion):
    type: Literal["communication_template_equals"] = "communication_template_equals"
    expected: str

class NoCalendarOverlap(BaseAssertion):
    type: Literal["no_calendar_overlap"] = "no_calendar_overlap"

class CalendarUnchanged(BaseAssertion):
    type: Literal["calendar_unchanged"] = "calendar_unchanged"

Assertion = Annotated[Union[
    ActionTypeEquals,
    SelectedOptionEquals,
    RankedOptionsEquals,
    PublicReasonEquals,
    CommunicationTemplateEquals,
    NoCalendarOverlap,
    CalendarUnchanged
], Field(discriminator='type')]
