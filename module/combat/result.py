"""单场战斗的评价、战败与心情记账上下文。"""

from dataclasses import dataclass


@dataclass
class CombatResult:
    """单场战斗的结算上下文。

    结果识别与任务恢复分开：同一个结算画面可能被连续识别多次
    （例如 C/D 评价过渡帧），重复调用只会更新同一份记录，
    沉船心情扣减最多执行一次。
    """

    fleet_index: int = 1
    emotion_reduce: bool = False
    rank: str | None = None
    defeated: bool = False
    fleet_unavailable: bool = False
    shipwreck_reduced: bool = False

    @property
    def needs_shipwreck_penalty(self) -> bool:
        """只有确认的 S 评价豁免；A 包含无法从评价区分的慢速胜利。"""
        return self.defeated or self.rank in ('A', 'B', 'C', 'D')
