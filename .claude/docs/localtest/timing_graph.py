import matplotlib.pyplot as plt
import numpy as np

scenarios = [
    "S1\nNormal PII",
    "S2\nNo PII",
    "S3t1\nMulti-turn",
    "S3t2\nHistory\npseudo",
    "S4\nWeb search",
    "S5\nFile upload",
    "S6\nMulti PII\ntypes",
    "S7\nFile+Web\n+Multi",
    "S8\nPrivacy\nOFF",
]

pseudo_ms  = [905,  1232, 868,  2839, 2047, 1705, 1168, 2042, 0]
ttft_s     = [2.28, 2.69, 1.62, 4.58, 3.35, 2.48, 2.79, 7.30, 1.19]
total_s    = [19.69, 2.93, 4.00, 13.98, 10.60, 5.49, 7.19, 26.20, 2.27]
tokens     = [4, 0, 3, 4, 9, 6, 7, 13, 0]

pseudo_s   = [p / 1000 for p in pseudo_ms]
llm_s      = [t - p for t, p in zip(total_s, pseudo_s)]

x = np.arange(len(scenarios))
fig, axes = plt.subplots(3, 1, figsize=(14, 14))
fig.suptitle("Garnet Proxy — Timing per Scenario", fontsize=16, fontweight="bold", y=0.98)

# ── Chart 1: stacked bar pseudo vs LLM ───────────────────────────────────────
ax1 = axes[0]
bars_pseudo = ax1.bar(x, pseudo_s, label="Garnet pseudo (s)", color="#e74c3c", alpha=0.85)
bars_llm    = ax1.bar(x, llm_s, bottom=pseudo_s, label="LLM time (s)", color="#3498db", alpha=0.85)

for i, (p, l, t) in enumerate(zip(pseudo_s, llm_s, total_s)):
    ax1.text(i, t + 0.2, f"{t:.1f}s", ha="center", va="bottom", fontsize=8, fontweight="bold")
    if p > 0.1:
        ax1.text(i, p / 2, f"{pseudo_ms[i]}ms", ha="center", va="center", fontsize=7, color="white")

ax1.set_xticks(x)
ax1.set_xticklabels(scenarios, fontsize=8)
ax1.set_ylabel("Time (seconds)")
ax1.set_title("Total time breakdown: Garnet overhead vs LLM time")
ax1.legend(loc="upper left")
ax1.set_ylim(0, max(total_s) * 1.15)
ax1.grid(axis="y", alpha=0.3)

# ── Chart 2: TTFT per scenario ────────────────────────────────────────────────
ax2 = axes[1]
bars_ttft = ax2.bar(x, ttft_s, color="#2ecc71", alpha=0.85)
for i, v in enumerate(ttft_s):
    ax2.text(i, v + 0.05, f"{v:.2f}s", ha="center", va="bottom", fontsize=8)

ax2.set_xticks(x)
ax2.set_xticklabels(scenarios, fontsize=8)
ax2.set_ylabel("Seconds")
ax2.set_title("Time to First Token (TTFT) — LLM responsiveness")
ax2.set_ylim(0, max(ttft_s) * 1.2)
ax2.grid(axis="y", alpha=0.3)
ax2.axhline(y=sum(ttft_s)/len(ttft_s), color="orange", linestyle="--", linewidth=1.2, label=f"avg {sum(ttft_s)/len(ttft_s):.2f}s")
ax2.legend()

# ── Chart 3: tokens restored per scenario ─────────────────────────────────────
ax3 = axes[2]
colors = ["#9b59b6" if t > 0 else "#95a5a6" for t in tokens]
bars_tok = ax3.bar(x, tokens, color=colors, alpha=0.85)
for i, v in enumerate(tokens):
    ax3.text(i, v + 0.1, str(v), ha="center", va="bottom", fontsize=9, fontweight="bold")

ax3.set_xticks(x)
ax3.set_xticklabels(scenarios, fontsize=8)
ax3.set_ylabel("PII tokens")
ax3.set_title("PII tokens pseudonymized & restored per scenario")
ax3.set_ylim(0, max(tokens) * 1.2 + 1)
ax3.grid(axis="y", alpha=0.3)

plt.tight_layout()
plt.savefig("timing_graph.png", dpi=150, bbox_inches="tight")
print("Saved: timing_graph.png")
plt.show()
