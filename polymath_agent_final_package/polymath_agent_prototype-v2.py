import math
import random
import json

class SubjectVector:
    """Вектор потребности отдельного субъекта в экосистеме PID0."""
    def __init__(self, name: str, intent_weights: list[float]):
        self.name = name
        self.intent = intent_weights  # [Порядок, Ресурс, Гармония, Автономия, Устойчивость]

    def get_tension(self, current_state: list[float]) -> float:
        """Расчет евклидова напряжения между желаемым вектором и реальным состоянием."""
        return math.sqrt(sum((w - s) ** 2 for w, s in zip(self.intent, current_state)))


class PID0_ComplexEcosystem:
    """
    PID0: Мультисубъектная среда с внешними помехами и физическими ограничениями.
    Моделирует траектории: Человек, Среда, Биосфера (Комар/Трава/Черепаха) + Шум.
    """
    def __init__(self):
        self.state = [0.2, 0.5, 0.1, 0.3, 0.2]  # [Порядок, Ресурс, Гармония, Автономия, Устойчивость]
        self.subjects = [
            SubjectVector("Человек (Разум)", [0.95, 0.70, 0.90, 0.85, 0.90]),
            SubjectVector("Среда (Физика)", [0.50, 0.90, 0.80, 0.99, 0.95]),
            SubjectVector("Биосфера (Трава/Комар)", [0.10, 0.85, 0.95, 0.70, 0.80])
        ]
        self.entropy = 0.92
        self.harmony = 0.08
        self.noise_level = 0.15

    def inject_noise(self):
        """Внесение внешних хаотических помех (энтропийный импульс)."""
        perturbation = random.uniform(0.05, self.noise_level)
        self.entropy = min(1.0, self.entropy + perturbation)
        for i in range(len(self.state)):
            self.state[i] = max(0.0, min(1.0, self.state[i] + random.uniform(-0.05, 0.05)))

    def apply_synthesis(self, synthesis_vector: list[float], bridge_quality: float):
        """Интеграция синтезированного моста в среду."""
        for i in range(len(self.state)):
            self.state[i] += 0.25 * bridge_quality * (synthesis_vector[i] - self.state[i])
        
        tensions = [s.get_tension(self.state) for s in self.subjects]
        avg_tension = sum(tensions) / len(tensions)
        
        self.harmony = min(1.0, max(0.0, 1.0 - avg_tension * 0.5 + bridge_quality * 0.2))
        self.entropy = min(1.0, max(0.0, self.entropy - bridge_quality * 0.25 + avg_tension * 0.1))
        return avg_tension


class ArchitectSubAgent:
    """Мультиагент 1: Архитектор — декомпозиция графа напряжений."""
    def analyze_tensions(self, env: PID0_ComplexEcosystem) -> dict:
        tensions = {s.name: round(s.get_tension(env.state), 4) for s in env.subjects}
        dominant_conflict = max(tensions, key=tensions.get)
        return {"tensions": tensions, "dominant_conflict": dominant_conflict}


class DialecticSubAgent:
    """Мультиагент 2: Диалектик — снятие противоречий (Тезис -> Антитезис -> Синтез)."""
    def resolve(self, env: PID0_ComplexEcosystem, conflict_info: dict) -> tuple[list[float], str]:
        # Вычисление идеального вектора не-нулевой суммы (Non-Zero Sum Synthesis)
        weighted_target = [0.0] * 5
        for s in env.subjects:
            for i in range(5):
                weighted_target[i] += s.intent[i] / len(env.subjects)
        
        synthesis_name = f"Синтез-Мост над [{conflict_info['dominant_conflict']}]"
        return weighted_target, synthesis_name


class StressTesterSubAgent:
    """Мультиагент 3: Стресс-тестер — симуляция экстремальных помех."""
    def apply_stress(self, env: PID0_ComplexEcosystem, severity: float = 0.3):
        env.entropy = min(1.0, env.entropy + severity)
        env.harmony = max(0.0, env.harmony - severity * 0.5)


class LFSKernelEngine:
    """Мультиагент 4: LFS-Ядро — управление вектором мастерства и незакристаллизованности."""
    def __init__(self):
        self.mastery = 0.1
        self.status = "UNCRYSTALLIZED_PROCESS (dS/dt ≠ 0)"

    def evolve(self, bridge_quality: float):
        self.mastery = min(1.0, self.mastery + 0.05 * bridge_quality)


class PolymathMultiAgentSystem:
    """
    ПОЛИМАТ МУЛЬТИАГЕНТ (PID1 = LFS):
    Сквозная параллельная интеграция Архитектора, Диалектика, Стресс-Тестера и Ядра.
    """
    def __init__(self):
        self.architect = ArchitectSubAgent()
        self.dialectic = DialecticSubAgent()
        self.stress_tester = StressTesterSubAgent()
        self.kernel = LFSKernelEngine()
        self.env = PID0_ComplexEcosystem()

    def run_full_synthesis_cycle(self, steps: int = 10, stress_at_step: int = 5) -> dict:
        history = []
        
        for step in range(1, steps + 1):
            # 1. Шум среды
            self.env.inject_noise()
            
            # 2. Стресс-тест в заданной точке
            if step == stress_at_step:
                self.stress_tester.apply_stress(self.env, severity=0.35)
            
            # 3. Анализ Архитектора
            arch_data = self.architect.analyze_tensions(self.env)
            
            # 4. Диалектический синтез
            synth_vector, bridge_title = self.dialectic.resolve(self.env, arch_data)
            bridge_quality = max(0.5, 1.0 - (arch_data['tensions'][arch_data['dominant_conflict']] / 2.0))
            
            # 5. Применение решения и обновление Ядра
            avg_tension = self.env.apply_synthesis(synth_vector, bridge_quality)
            self.kernel.evolve(bridge_quality)
            
            history.append({
                "step": step,
                "entropy": round(self.env.entropy, 4),
                "harmony": round(self.env.harmony, 4),
                "avg_tension": round(avg_tension, 4),
                "mastery": round(self.kernel.mastery, 4),
                "dominant_conflict": arch_data['dominant_conflict'],
                "bridge_quality": round(bridge_quality, 4)
            })

        return {
            "status": self.kernel.status,
            "final_mastery": round(self.kernel.mastery, 4),
            "final_entropy": round(self.env.entropy, 4),
            "final_harmony": round(self.env.harmony, 4),
            "history": history
        }

if __name__ == "__main__":
    system = PolymathMultiAgentSystem()
    result = system.run_full_synthesis_cycle(steps=10, stress_at_step=5)
    print(json.dumps(result, ensure_ascii=False, indent=2))
