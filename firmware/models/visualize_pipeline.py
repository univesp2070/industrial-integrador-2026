#!/usr/bin/env python3
"""
Painel de visualização do pipeline de treinamento ML — Edge AI Industrial
Gera: firmware/models/ml_report.png
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import seaborn as sns
from pathlib import Path

from train_model import DataLoader, ModelBuilder

# ── Paleta ───────────────────────────────────────────────────────────────────
C_NORMAL  = "#2196F3"   # azul
C_ANOMALY = "#F44336"   # vermelho
C_ACCENT  = "#FF9800"   # laranja
BG        = "#F8F9FA"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.facecolor": BG,
    "figure.facecolor": "white",
    "axes.spines.top": False,
    "axes.spines.right": False,
})

print("[viz] Gerando dataset sintético (10 000 amostras)...")
loader = DataLoader(samples=10_000, anomaly_fraction=0.2, seed=42)
X, y = loader.generate_synthetic()
stats = loader.stats(X, y)

print("[viz] Treinando modelo (20 épocas)...")
import warnings
warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

builder = ModelBuilder(epochs=20)
model   = builder.build()
history = builder.train(model, X, y)

# Predições sobre o dataset inteiro
preds = model.predict(X, verbose=0).flatten()

# ── Layout: 3 linhas × 3 colunas ─────────────────────────────────────────────
fig = plt.figure(figsize=(18, 14))
fig.suptitle(
    "Pipeline de Treinamento ML — Detecção de Anomalias (ESP32 Edge AI)",
    fontsize=16, fontweight="bold", y=0.98
)
gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.45, wspace=0.35)

# ── 1. Distribuição do dataset (pizza) ────────────────────────────────────────
ax1 = fig.add_subplot(gs[0, 0])
sizes  = [stats["normal"], stats["anomaly"]]
labels = [f'Normal\n{stats["normal"]:,} ({stats["normal"]/stats["total"]:.1%})',
          f'Anomalia\n{stats["anomaly"]:,} ({stats["anomaly"]/stats["total"]:.1%})']
wedges, texts = ax1.pie(
    sizes, labels=labels, colors=[C_NORMAL, C_ANOMALY],
    startangle=90, wedgeprops=dict(width=0.55, edgecolor="white", linewidth=2),
)
for t in texts:
    t.set_fontsize(9)
ax1.set_title("1. Distribuição do Dataset", fontweight="bold", pad=12)

# ── 2. Histograma temperatura ─────────────────────────────────────────────────
ax2 = fig.add_subplot(gs[0, 1])
ax2.hist(X[y==0, 0]*100, bins=40, color=C_NORMAL,  alpha=0.7, label="Normal",   density=True)
ax2.hist(X[y==1, 0]*100, bins=40, color=C_ANOMALY, alpha=0.7, label="Anomalia", density=True)
ax2.axvline(34.0, color="black", linestyle="--", linewidth=1.2, label="Limiar (34°C)")
ax2.set_xlabel("Temperatura (°C)", fontsize=9)
ax2.set_ylabel("Densidade", fontsize=9)
ax2.set_title("2. Distribuição — Temperatura", fontweight="bold")
ax2.legend(fontsize=8)

# ── 3. Histograma vibração ────────────────────────────────────────────────────
ax3 = fig.add_subplot(gs[0, 2])
ax3.hist(X[y==0, 1]*2,   bins=40, color=C_NORMAL,  alpha=0.7, label="Normal",   density=True)
ax3.hist(X[y==1, 1]*2,   bins=40, color=C_ANOMALY, alpha=0.7, label="Anomalia", density=True)
ax3.axvline(0.55, color="black", linestyle="--", linewidth=1.2, label="Limiar (0.55 mm/s)")
ax3.set_xlabel("Vibração (mm/s)", fontsize=9)
ax3.set_ylabel("Densidade", fontsize=9)
ax3.set_title("3. Distribuição — Vibração", fontweight="bold")
ax3.legend(fontsize=8)

# ── 4. Scatter: temp × vibração com score de anomalia ────────────────────────
ax4 = fig.add_subplot(gs[1, :2])
sample_idx = np.random.default_rng(0).choice(len(X), 1500, replace=False)
sc = ax4.scatter(
    X[sample_idx, 0]*100,
    X[sample_idx, 1]*2,
    c=preds[sample_idx],
    cmap="RdYlBu_r", alpha=0.65, s=18, vmin=0, vmax=1
)
cbar = plt.colorbar(sc, ax=ax4, fraction=0.035, pad=0.02)
cbar.set_label("anomaly_score", fontsize=9)
cbar.ax.axhline(0.8, color="black", linewidth=1.5, linestyle="--")
cbar.ax.text(1.6, 0.8, "threshold\n0.8", fontsize=7, va="center")
ax4.set_xlabel("Temperatura (°C)", fontsize=9)
ax4.set_ylabel("Vibração (mm/s)", fontsize=9)
ax4.set_title("4. Mapa de Anomaly Score — Temperatura × Vibração (1.500 amostras)", fontweight="bold")

# ── 5. Arquitetura do modelo (diagrama) ───────────────────────────────────────
ax5 = fig.add_subplot(gs[1, 2])
ax5.set_xlim(0, 10)
ax5.set_ylim(0, 10)
ax5.axis("off")
ax5.set_title("5. Arquitetura do Modelo", fontweight="bold")

layers = [
    (1.5, 5.0, "Input\n(3 features)", "#E3F2FD", 3),
    (4.0, 5.0, "Dense(8)\nReLU", "#BBDEFB", 8),
    (6.5, 5.0, "Dense(4)\nReLU", "#90CAF9", 4),
    (9.0, 5.0, "Dense(1)\nSigmoid", C_ANOMALY, 1),
]
for (x, y_pos, label, color, n) in layers:
    box = mpatches.FancyBboxPatch(
        (x-0.7, y_pos-1.4), 1.4, 2.8,
        boxstyle="round,pad=0.1", facecolor=color,
        edgecolor="white", linewidth=2
    )
    ax5.add_patch(box)
    ax5.text(x, y_pos+0.15, label, ha="center", va="center",
             fontsize=8, fontweight="bold")
    ax5.text(x, y_pos-0.8, f"{n} neurônio{'s' if n>1 else ''}",
             ha="center", va="center", fontsize=7, color="#555")

# Setas
for i in range(len(layers)-1):
    x0 = layers[i][0] + 0.7
    x1 = layers[i+1][0] - 0.7
    y0 = layers[i][1]
    ax5.annotate("", xy=(x1, y0), xytext=(x0, y0),
                 arrowprops=dict(arrowstyle="->", color="#555", lw=1.5))

ax5.text(5.0, 1.5, "73 parâmetros · 2,4 KB TFLite",
         ha="center", fontsize=8, color="#555", style="italic")

# ── 6. Curva de loss (treino × validação) ─────────────────────────────────────
ax6 = fig.add_subplot(gs[2, 0])
epochs_range = range(1, len(history["loss"]) + 1)
ax6.plot(epochs_range, history["loss"],     color=C_NORMAL,  linewidth=2, label="Treino")
ax6.plot(epochs_range, history["val_loss"], color=C_ANOMALY, linewidth=2, label="Validação", linestyle="--")
ax6.set_xlabel("Época", fontsize=9)
ax6.set_ylabel("Binary Crossentropy", fontsize=9)
ax6.set_title("6. Curva de Loss", fontweight="bold")
ax6.legend(fontsize=8)
ax6.set_xlim(1, len(history["loss"]))

# ── 7. Curva de acurácia ──────────────────────────────────────────────────────
ax7 = fig.add_subplot(gs[2, 1])
ax7.plot(epochs_range, history["accuracy"],     color=C_NORMAL,  linewidth=2, label="Treino")
ax7.plot(epochs_range, history["val_accuracy"], color=C_ANOMALY, linewidth=2, label="Validação", linestyle="--")
ax7.set_ylim(0, 1.05)
ax7.set_xlabel("Época", fontsize=9)
ax7.set_ylabel("Acurácia", fontsize=9)
ax7.set_title("7. Curva de Acurácia", fontweight="bold")
ax7.legend(fontsize=8)
ax7.set_xlim(1, len(history["loss"]))
ax7.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))

# ── 8. Histograma do anomaly_score predito ────────────────────────────────────
ax8 = fig.add_subplot(gs[2, 2])
ax8.hist(preds[y==0], bins=40, color=C_NORMAL,  alpha=0.75, density=True, label="Normal")
ax8.hist(preds[y==1], bins=40, color=C_ANOMALY, alpha=0.75, density=True, label="Anomalia")
ax8.axvline(0.8, color="black", linestyle="--", linewidth=1.5, label="Threshold 0.8")
ax8.set_xlabel("anomaly_score predito", fontsize=9)
ax8.set_ylabel("Densidade", fontsize=9)
ax8.set_title("8. Distribuição do Score Predito", fontweight="bold")
ax8.legend(fontsize=8)

# ── Rodapé ────────────────────────────────────────────────────────────────────
fig.text(
    0.5, 0.005,
    "Dados sintéticos · TensorFlow 2.21 · firmware/models/train_model.py --synthetic  "
    "· Branch: feature/esp32-edge-network-sim-bootstrap",
    ha="center", fontsize=8, color="#888"
)

out = Path(__file__).parent / "ml_report.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
print(f"[viz] Salvo em: {out}")
print("[viz] Abra o arquivo ml_report.png para visualizar o painel completo.")
