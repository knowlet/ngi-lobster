from __future__ import annotations

from dataclasses import dataclass

from lobster_core import RuntimeState, StateTransition


class InvalidTransitionError(ValueError):
    pass


_ALLOWED_TRANSITIONS: dict[RuntimeState, set[RuntimeState]] = {
    RuntimeState.PRE_AGREEMENT: {RuntimeState.ACTIVE_TRUCE, RuntimeState.DISPUTED_TRUCE, RuntimeState.ESCALATION},
    RuntimeState.ACTIVE_TRUCE: {RuntimeState.DISPUTED_TRUCE, RuntimeState.ESCALATION},
    RuntimeState.DISPUTED_TRUCE: {RuntimeState.ACTIVE_TRUCE, RuntimeState.ESCALATION},
    RuntimeState.ESCALATION: {RuntimeState.ACTIVE_TRUCE, RuntimeState.DISPUTED_TRUCE},
}


@dataclass(slots=True)
class StateMachine:
    current_state: RuntimeState

    def can_transition(self, to_state: RuntimeState) -> bool:
        if to_state == self.current_state:
            return True
        return to_state in _ALLOWED_TRANSITIONS.get(self.current_state, set())

    def transition(
        self,
        *,
        to_state: RuntimeState,
        reason: str,
        transition_id: str,
        actor: str | None = None,
        trigger: str | None = None,
        source_snapshot_id: str | None = None,
        recorded_at_utc: str | None = None,
    ) -> StateTransition:
        if not self.can_transition(to_state):
            raise InvalidTransitionError(f"invalid transition: {self.current_state} -> {to_state}")

        previous = self.current_state
        self.current_state = to_state
        return StateTransition(
            schema_version="v1",
            transition_id=transition_id,
            from_state=previous,
            to_state=to_state,
            reason=reason,
            actor=actor,
            trigger=trigger,
            source_snapshot_id=source_snapshot_id,
            recorded_at_utc=recorded_at_utc,
        )
