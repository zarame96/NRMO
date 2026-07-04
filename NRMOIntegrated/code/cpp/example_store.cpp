// example_store.cpp
//
// NRMO/Loom C++ core の使用例: 店舗運営 (retail operation) adapter.
// Python 版 StoreOperationAdapter と同じ domain modeling.
//
// build:  g++ -std=c++17 -O2 example_store.cpp -o example_store
// run:    ./example_store

#include "nrmo_core.hpp"
#include <iostream>
#include <iomanip>
#include <vector>
#include <cmath>

using namespace nrmo;

// ============================================================
// 店舗運営の domain state
// ============================================================
struct StoreState {
    double cash = 100.0;
    double inventory = 50.0;
    double staff_morale = 60.0;
    double customer_base = 50.0;
    double market_knowledge = 50.0;
    double competitive_pressure = 30.0;
    double revenue_accum = 0.0;
    int    step = 0;
    bool   is_ruined = false;
};

// ============================================================
// 店舗運営 adapter
// ============================================================
class StoreAdapter : public DomainAdapter<StoreState> {
public:
    std::string name() const override { return "Store Operation"; }

    WorldState to_loom_state(const StoreState& ds) const override {
        WorldState s;
        s.t = ds.step;
        s.R = clip(ds.cash, 0, 200) / 2.0;
        s.E = clip(ds.staff_morale, 0, 100);
        s.G = clip(100 - std::abs(ds.inventory - 50), 0, 100);
        s.O = clip(ds.customer_base, 0, 100);
        s.K = clip(ds.market_knowledge, 0, 100);
        s.X = clip(ds.competitive_pressure, 0, 100);
        s.cumulative_score = ds.revenue_accum;
        s.is_ruined = (ds.cash < 15);
        return s;
    }

    StoreState apply_action(const Action& a, const StoreState& ds,
                            std::mt19937& rng) const override {
        StoreState ns = ds;
        ns.step = ds.step + 1;
        double mag = a.magnitude();
        std::normal_distribution<double> n01(0.0, 1.0);

        switch (a.intent) {
            case Intent::Invest:
                ns.inventory += 10*mag; ns.customer_base += 5*mag; ns.cash -= 12*mag; break;
            case Intent::Explore:
                ns.market_knowledge += 6*mag; ns.customer_base += 3*mag; ns.cash -= 6*mag; break;
            case Intent::Defend:
                ns.cash += 3*mag; ns.competitive_pressure -= 4*mag; ns.staff_morale -= 2*mag; break;
            case Intent::Recover:
                ns.cash += 8*mag; ns.inventory -= 5*mag; ns.staff_morale += 3*mag; break;
            case Intent::Hold: break;
        }
        // market dynamics
        double demand = ns.customer_base * 0.3 * (1 + n01(rng)*0.2);
        double sales = std::min(demand, ns.inventory);
        ns.inventory -= sales;
        ns.cash += sales * 1.5;
        ns.revenue_accum += sales * 1.5;
        ns.competitive_pressure += 1 + n01(rng)*2;
        ns.staff_morale = clip(ns.staff_morale + n01(rng)*2, 0, 100);
        ns.cash -= 5; // 固定費

        ns.cash = clip(ns.cash, 0, 400);
        ns.inventory = clip(ns.inventory, 0, 200);
        ns.customer_base = clip(ns.customer_base, 0, 200);
        ns.market_knowledge = clip(ns.market_knowledge, 0, 100);
        ns.competitive_pressure = clip(ns.competitive_pressure, 0, 100);
        return ns;
    }

    bool is_ruin(const StoreState& ds) const override { return ds.cash < 15; }

    double compute_reward(const StoreState& prev, const StoreState& ns) const override {
        return (ns.revenue_accum - prev.revenue_accum)/20.0 - (ns.cash < 30 ? 0.5 : 0.0);
    }

    Action propose_high_output(const StoreState& ds, std::mt19937&) const override {
        if (ds.cash > 60) return {Intent::Invest, Strength::C};
        if (ds.cash > 35) return {Intent::Invest, Strength::B};
        return {Intent::Explore, Strength::A};
    }
};

int main() {
    std::cout << "========================================================\n";
    std::cout << "NRMO/Loom C++ — Store Operation Demo\n";
    std::cout << "========================================================\n";

    StoreAdapter adapter;
    std::vector<unsigned> seeds = {42, 123, 777, 2024, 9999};

    for (bool hybrid : {true, false}) {
        double sum_score = 0, sum_surv = 0; int n_ruin = 0;
        for (unsigned seed : seeds) {
            LoomController ctrl(seed, hybrid, /*safety_floor=*/true);
            auto res = ctrl.run_episode<StoreState>(adapter, StoreState{}, 150);
            sum_score += res.final_state.revenue_accum;
            sum_surv  += res.survived_steps;
            if (res.ruined) n_ruin++;
        }
        std::cout << "  [" << (hybrid ? "Hybrid  " : "Loom only")
                  << "] avg_revenue=" << std::fixed << std::setprecision(1)
                  << sum_score/seeds.size()
                  << ", ruin_rate=" << (100*n_ruin/seeds.size()) << "%"
                  << ", survival=" << sum_surv/seeds.size() << "/150\n";
    }
    std::cout << "\n[C++ core 動作確認 OK]\n";
    return 0;
}
