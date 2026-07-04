// nrmo_core.hpp
//
// NRMO/Loom Universal Adapter Framework — C++ core.
//
// Header-only な軽量 port. Loom v3.1 の本質 (Sparse Activation +
// Safety Floor + Hybrid) を C++ で再現し、DomainAdapter を継承すれば
// 任意 domain に接続できる構造.
//
// 思想は Python 版 (nrmo_universal_adapter.py) と同一.
//   - 6D state (R,E,G,O,K,X)
//   - absorbing failure state (ruin) を回避
//   - Safety Floor (危機時 recover-first)
//   - Hybrid (高出力 proposal + Safety Floor)

#ifndef NRMO_CORE_HPP
#define NRMO_CORE_HPP

#include <array>
#include <string>
#include <random>
#include <algorithm>
#include <memory>
#include <map>

namespace nrmo {

// ============================================================
// 6D World State (R,E,G,O,K,X)
// ============================================================
struct WorldState {
    double R = 50.0;  // 資源・流動性 (高いほど安全)
    double E = 50.0;  // 持続性
    double G = 50.0;  // 統治・規律
    double O = 50.0;  // 選択肢・柔軟性
    double K = 50.0;  // 知識・理解
    double X = 20.0;  // リスク曝露 (高いほど危険)
    int    t = 0;
    double cumulative_score = 0.0;
    bool   is_ruined = false;
};

// ============================================================
// Action (intent, strength)
// ============================================================
enum class Intent { Invest, Defend, Explore, Recover, Hold };
enum class Strength { A, B, C };  // A=小, B=中, C=大

struct Action {
    Intent   intent   = Intent::Hold;
    Strength strength = Strength::A;

    double magnitude() const {
        switch (strength) {
            case Strength::A: return 0.5;
            case Strength::B: return 1.0;
            case Strength::C: return 1.6;
        }
        return 1.0;
    }
    std::string to_string() const {
        static const char* in[] = {"invest","defend","explore","recover","hold"};
        static const char* st[] = {"A","B","C"};
        return std::string(in[(int)intent]) + "/" + st[(int)strength];
    }
};

// ============================================================
// Loom mode (Sparse Activation)
// ============================================================
enum class LoomMode { Safety, Drift, Stabilization, SevereCycle,
                       Opportunity, Normal };

// ============================================================
// DomainAdapter — 新 domain はこれを継承
// ============================================================
template <typename DomainState>
class DomainAdapter {
public:
    virtual ~DomainAdapter() = default;

    // 必須: domain state → 6D WorldState
    virtual WorldState to_loom_state(const DomainState& ds) const = 0;
    // 必須: Loom action を適用し次状態を返す
    virtual DomainState apply_action(const Action& a, const DomainState& ds,
                                     std::mt19937& rng) const = 0;
    // 必須: 破綻状態か
    virtual bool is_ruin(const DomainState& ds) const = 0;
    // 必須: reward
    virtual double compute_reward(const DomainState& prev,
                                  const DomainState& next) const = 0;

    // 任意: Hybrid 用 高出力 proposal
    virtual Action propose_high_output(const DomainState& ds,
                                       std::mt19937& rng) const {
        return Action{Intent::Invest, Strength::C};
    }
    // 任意: 危機度 (default: R 低 / X 高)
    virtual double risk_proximity(const DomainState& ds) const {
        WorldState ls = to_loom_state(ds);
        double r_part = std::max(0.0, (35.0 - ls.R) / 35.0) * 0.5;
        double x_part = std::max(0.0, (ls.X - 60.0) / 40.0) * 0.5;
        return std::min(1.0, r_part + x_part);
    }
    virtual std::string name() const { return "unnamed"; }
};

// ============================================================
// Loom Controller (Sparse Activation + Safety Floor + Hybrid)
// ============================================================
class LoomController {
public:
    explicit LoomController(unsigned seed = 42,
                            bool use_hybrid = true,
                            bool use_safety_floor = true)
        : rng_(seed), use_hybrid_(use_hybrid),
          use_safety_floor_(use_safety_floor) {}

    static constexpr double EMERGENCY_RISK = 0.45;
    static constexpr double R_FLOOR = 25.0;
    static constexpr double X_CEILING = 80.0;

    // --- Sparse Activation: world state から mode を決定 ---
    LoomMode select_mode(const WorldState& s, double risk) const {
        if (s.R <= 18 || s.X >= 85 || risk >= 0.65)
            return LoomMode::Safety;
        // drift signature: X 上昇 trend (簡易: X が中程度で上昇傾向)
        if (s.X > 30 && s.X < 70 && s.R > 40)
            return LoomMode::Drift;
        if (s.X >= 55)
            return LoomMode::Stabilization;
        if (s.R >= 60 && s.X <= 40)
            return LoomMode::Opportunity;
        return LoomMode::Normal;
    }

    // --- Safety Floor: 危機時に recover-first へ throttle ---
    Action apply_safety_floor(const Action& proposed,
                              const WorldState& s) const {
        if (!use_safety_floor_) return proposed;
        bool emergency = (s.R <= R_FLOOR || s.X >= X_CEILING);
        if (!emergency) return proposed;
        // recover-first: 攻めの action を recover/defend に置換
        if (proposed.intent == Intent::Invest ||
            proposed.intent == Intent::Explore) {
            return Action{Intent::Recover, Strength::A};
        }
        return proposed;
    }

    // --- mode から保守的 action を生成 ---
    Action conservative_action(LoomMode mode) const {
        switch (mode) {
            case LoomMode::Safety:        return {Intent::Recover, Strength::A};
            case LoomMode::Drift:         return {Intent::Invest,  Strength::A};
            case LoomMode::Stabilization: return {Intent::Defend,  Strength::A};
            case LoomMode::SevereCycle:   return {Intent::Defend,  Strength::A};
            case LoomMode::Opportunity:   return {Intent::Invest,  Strength::B};
            case LoomMode::Normal:        return {Intent::Recover, Strength::A};
        }
        return {Intent::Hold, Strength::A};
    }

    // --- 統合 decide (Hybrid) ---
    template <typename DomainState>
    Action decide(const DomainAdapter<DomainState>& adapter,
                  const DomainState& ds) {
        WorldState s = adapter.to_loom_state(ds);
        double risk = adapter.risk_proximity(ds);
        LoomMode mode = select_mode(s, risk);

        Action action;
        if (use_hybrid_ && risk < EMERGENCY_RISK) {
            // 平時: 高出力 proposal
            action = adapter.propose_high_output(ds, rng_);
            stats_high_output_++;
        } else {
            // 危機時: 保守的判断
            action = conservative_action(mode);
            stats_conservative_++;
        }
        // Safety Floor (最終 gate)
        Action final = apply_safety_floor(action, s);
        if (!(final.intent == action.intent &&
              final.strength == action.strength)) {
            stats_safety_floor_++;
        }
        last_mode_ = mode;
        return final;
    }

    // --- episode runner ---
    template <typename DomainState>
    struct EpisodeResult {
        DomainState final_state;
        bool   ruined = false;
        int    survived_steps = 0;
        double final_score = 0.0;
    };

    template <typename DomainState>
    EpisodeResult<DomainState> run_episode(
            const DomainAdapter<DomainState>& adapter,
            DomainState init, int horizon) {
        DomainState ds = init;
        EpisodeResult<DomainState> res;
        int step = 0;
        for (; step < horizon; ++step) {
            Action a = decide(adapter, ds);
            DomainState next = adapter.apply_action(a, ds, rng_);
            (void)adapter.compute_reward(ds, next);
            ds = next;
            if (adapter.is_ruin(ds)) { res.ruined = true; break; }
        }
        res.final_state = ds;
        res.survived_steps = step + 1;
        res.final_state.is_ruined = res.ruined;
        return res;
    }

    LoomMode last_mode() const { return last_mode_; }
    int stats_high_output() const { return stats_high_output_; }
    int stats_conservative() const { return stats_conservative_; }
    int stats_safety_floor() const { return stats_safety_floor_; }

private:
    std::mt19937 rng_;
    bool use_hybrid_;
    bool use_safety_floor_;
    LoomMode last_mode_ = LoomMode::Normal;
    int stats_high_output_ = 0;
    int stats_conservative_ = 0;
    int stats_safety_floor_ = 0;
};

inline double clip(double v, double lo, double hi) {
    return std::max(lo, std::min(hi, v));
}

} // namespace nrmo

#endif // NRMO_CORE_HPP
