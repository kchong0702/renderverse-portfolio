from src.features.draft_reply.schemas import DraftReply
from src.shared.checks import CheckError, CheckRule
from src.shared.email import TimeSlot


def check_slots(reply: DraftReply, free_slots: list[TimeSlot]) -> list[CheckError]:
    """Errors for offered slot ids that aren't one of the free slots"""
    return [
        CheckError(
            rule=CheckRule.UNKNOWN_SLOT,
            at=f"slot_ids[{index}]",
            message=f"{slot_id} is not a free slot id; offer only listed slots",
        )
        for index, slot_id in enumerate(reply.slot_ids)
        if not 1 <= slot_id <= len(free_slots)
    ]
