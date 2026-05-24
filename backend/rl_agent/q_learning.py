import json
import random
from pathlib import Path

from backend.recommendation_engine.engine import STRATEGY_RESOURCES

ROOT_DIR = Path(__file__).resolve().parents[2]
Q_TABLE_PATH = ROOT_DIR / "trained_models" / "q_table.json"


class QLearningAgent:
    def __init__(self, alpha: float = 0.35, gamma: float = 0.8, epsilon: float = 0.12):
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.actions = list(STRATEGY_RESOURCES.keys())
        self.q_table = self._load()

    def _load(self) -> dict[str, dict[str, float]]:
        if Q_TABLE_PATH.exists():
            return json.loads(Q_TABLE_PATH.read_text(encoding="utf-8"))
        return {}

    def _save(self) -> None:
        Q_TABLE_PATH.parent.mkdir(parents=True, exist_ok=True)
        Q_TABLE_PATH.write_text(json.dumps(self.q_table, indent=2), encoding="utf-8")

    def choose_action(self, state: str, ml_strategy: str) -> tuple[str, str]:
        self.q_table.setdefault(state, {action: 0.0 for action in self.actions})
        if random.random() < self.epsilon:
            return random.choice(self.actions), "q-learning exploration"
        best_action, best_value = max(self.q_table[state].items(), key=lambda item: item[1])
        if best_value <= 0:
            return ml_strategy, "random forest baseline"
        return best_action, "q-learning adaptation"

    def update(self, state: str, action: str, reward: float, next_state: str | None = None) -> float:
        self.q_table.setdefault(state, {candidate: 0.0 for candidate in self.actions})
        old_value = self.q_table[state].get(action, 0.0)
        future_value = 0.0
        if next_state:
            self.q_table.setdefault(next_state, {candidate: 0.0 for candidate in self.actions})
            future_value = max(self.q_table[next_state].values())
        new_value = old_value + self.alpha * (reward + self.gamma * future_value - old_value)
        self.q_table[state][action] = round(new_value, 4)
        self._save()
        return self.q_table[state][action]


def calculate_reward(rating: int, helped: bool, score_before: float, score_after: float) -> float:
    rating_component = (rating - 3) / 2
    improvement_component = max(-1.0, min(1.0, (score_after - score_before) / 20))
    helped_component = 0.4 if helped else -0.4
    return round(rating_component + improvement_component + helped_component, 3)
