#!/usr/bin/env python3
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import sys
import os
import numpy as np
from scipy.stats import ttest_ind, levene, t
from scipy import stats

from pathlib import Path
import re

# Objeto Path para el directorio
dir_path = Path("output")

# Crear el directorio (incluyendo padres si hiciera falta), y sin error si ya existe
dir_path.mkdir(parents=True, exist_ok=True)


def compute_comparisons_with_levene(df_all: pd.DataFrame) -> pd.DataFrame:
    comparisons = []
    for kem in df_all["KEM"].unique():
        a = df_all[(df_all["KEM"] == kem) & (df_all["Platform"] == "ARM")]["Time (ms)"]
        b = df_all[(df_all["KEM"] == kem) & (df_all["Platform"] == "x86")]["Time (ms)"]
        if len(a) < 2 or len(b) < 2:
            continue
        _, p_levene = levene(a, b)
        equal_var = p_levene >= 0.05
        tstat, _ = ttest_ind(a, b, equal_var=equal_var)

        df          = len(a) + len(b) - 2
        log_p       = stats.t.logsf(abs(tstat), df) + np.log(2)
        pval        = np.exp(log_p)

        mean_arm, mean_x86 = a.mean(), b.mean()
        diff_pct = 100 * (mean_x86 - mean_arm) / mean_arm
        n1, n2 = len(a), len(b)
        s1, s2 = np.var(a, ddof=1), np.var(b, ddof=1)
        se = np.sqrt(s1 / n1 + s2 / n2)
        df_eff = (s1 / n1 + s2 / n2)**2 / (((s1 / n1)**2) / (n1 - 1) + ((s2 / n2)**2) / (n2 - 1))
        t_crit = t.ppf(0.975, df_eff)
        diff_mean = mean_x86 - mean_arm
        ci_lower = diff_mean - t_crit * se
        ci_upper = diff_mean + t_crit * se
        speedup  = mean_x86 / mean_arm

        comparisons.append({
            "KEM": kem,
            "Mean_ARM": mean_arm,
            "Mean_x86": mean_x86,
            "Diff_% (vs ARM)": diff_pct,
            "p_value": pval,
            "Levene_p": p_levene,
            "Equal_Var": "Yes" if equal_var else "No",
            "Significant": "Yes" if pval < 0.05 else "No",
            "CI_lower": ci_lower,
            "CI_upper": ci_upper,
            "SpeedUp": speedup
        })
    return pd.DataFrame(comparisons).sort_values("Diff_% (vs ARM)", ascending=False)


def generate_adaptive_summary(comparisons_df, outliers_df, base_name):
    lines = []
    total_kems = len(comparisons_df)
    significant_kems = comparisons_df["Significant"].value_counts().get("Yes", 0)
    arm_wins = (comparisons_df["Diff_% (vs ARM)"] > 0).sum()
    x86_wins = total_kems - arm_wins
    max_diff = comparisons_df["Diff_% (vs ARM)"].max()
    min_diff = comparisons_df["Diff_% (vs ARM)"].min()
    worst_kem = comparisons_df.iloc[0]["KEM"]
    best_kem = comparisons_df.iloc[-1]["KEM"]
    extreme_out_x86 = outliers_df[(outliers_df["Platform"] == "x86") & (outliers_df["Max_Outlier"] > 1000)]["KEM"].tolist()
    extreme_out_arm = outliers_df[(outliers_df["Platform"] == "ARM") & (outliers_df["Max_Outlier"] > 1000)]["KEM"].tolist()
    total_outliers_arm = outliers_df[outliers_df["Platform"] == "ARM"]["Outlier_Count"].sum()
    total_outliers_x86 = outliers_df[outliers_df["Platform"] == "x86"]["Outlier_Count"].sum()

    lines.append(f"\\section*{{Adaptive Summary for {base_name}}}")
    lines.append(f"{total_kems} KEMs were evaluated, of which {significant_kems} showed statistically significant differences ($p < 0.05$).")
    if arm_wins == total_kems:
        lines.append("ARM outperformed x86 in all KEMs.")
    elif x86_wins == total_kems:
        lines.append("x86 outperformed ARM in all KEMs.")
    else:
        lines.append(f"ARM was faster in {arm_wins} KEMs, while x86 was faster in {x86_wins}.")
    lines.append(f"The latency difference ranged from {min_diff:.1f}\\% to {max_diff:.1f}\\%.")
    lines.append(f"The most impacted KEM was \\texttt{{{worst_kem}}}, and the closest match was \\texttt{{{best_kem}}}.")
    if extreme_out_x86 or extreme_out_arm:
        line = "Extreme outliers (>1000 ms) were observed in:"
        if extreme_out_arm:
            line += " ARM: " + ", ".join(f"\\texttt{{{k}}}" for k in extreme_out_arm) + "."
        if extreme_out_x86:
            line += " x86: " + ", ".join(f"\\texttt{{{k}}}" for k in extreme_out_x86) + "."
        lines.append(line)
    else:
        lines.append("No extreme outliers above 1000 ms were detected.")

    lines.append(f"Total outliers — ARM: {total_outliers_arm}, x86: {total_outliers_x86}.")
    if total_outliers_arm < total_outliers_x86:
        lines.append("ARM demonstrated greater stability.")
    elif total_outliers_x86 < total_outliers_arm:
        lines.append("x86 demonstrated greater stability.")
    else:
        lines.append("Stability was comparable between platforms.")

    summary_path = f"./output/summary_adaptive_{base_name}.tex"
    with open(summary_path, "w") as f:
        f.write("\n".join(lines))
    return summary_path


def analyze_signature_csvs(csv_arm, csv_x86, base_name):
    # --- Carga y unificación de datos ----------------------------------------
    df_arm = pd.read_csv(csv_arm).melt(var_name="KEM", value_name="Time (ms)")
    df_arm["Platform"] = "ARM"
    df_x86 = pd.read_csv(csv_x86).melt(var_name="KEM", value_name="Time (ms)")
    df_x86["Platform"] = "x86"
    df_all = pd.concat([df_arm, df_x86], ignore_index=True).dropna()
    print(f"📥 Loaded data: {len(df_all)} combined samples")

    # --- Filtrado de extremos (> 1000 ms) ------------------------------------
    threshold = 1000
    before = len(df_all)
    df_all = df_all[df_all["Time (ms)"] <= threshold]
    dropped = before - len(df_all)
    print(f"🚫 Removed extremes > {threshold} ms: {dropped} samples dropped")
    print(f"✅ Remaining samples: {len(df_all)}")

    # --- Comparaciones ARM vs x86 --------------------------------------------
    comparisons_df = compute_comparisons_with_levene(df_all)
    # Contiene: KEM, Mean_ARM, Mean_x86, SpeedUp, p_value, etc.

    # --- Cálculo de CV --------------------------------------------------------
    cv = (
        df_all
        .groupby(['KEM', 'Platform'])['Time (ms)']
        .agg(mean='mean', std='std')
        .reset_index()
        .assign(CV=lambda d: d['std'] / d['mean'])
        .pivot(index='KEM', columns='Platform', values='CV')
        .rename(columns={'ARM': 'CV_ARM', 'x86': 'CV_x86'})
    )
    comparisons_df = comparisons_df.merge(cv, left_on='KEM', right_index=True)

    # --- Cálculo de SD, Median, IQR por plataforma ---------------------------
    stats_extra = (
        df_all
        .groupby(['KEM', 'Platform'])['Time (ms)']
        .agg(
            SD='std',
            Median='median',
            Q1=lambda x: x.quantile(0.25),
            Q3=lambda x: x.quantile(0.75)
        )
        .reset_index()
    )
    stats_extra["IQR"] = stats_extra["Q3"] - stats_extra["Q1"]
    stats_extra = stats_extra.drop(columns=["Q1", "Q3"])

    # Pivot para tener columnas separadas ARM/x86
    stats_pivot = stats_extra.pivot(index="KEM", columns="Platform")
    # Aplanar columnas MultiIndex tipo ('SD','ARM') → 'SD_ARM'
    stats_pivot.columns = [f"{metric}_{plat}" for (metric, plat) in stats_pivot.columns]
    # Merge con comparisons_df
    comparisons_df = comparisons_df.merge(stats_pivot, left_on="KEM", right_index=True)

    # --- Detección de outliers (IQR) en el conjunto limpio -------------------
    outlier_rows = []
    for kem in df_all["KEM"].unique():
        for plat in ("ARM", "x86"):
            times = df_all.loc[
                (df_all["KEM"] == kem) & (df_all["Platform"] == plat),
                "Time (ms)"
            ]
            if len(times) == 0:
                pct = 0.0
            else:
                q1, q3 = times.quantile([0.25, 0.75])
                iqr = q3 - q1
                lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
                out = times[(times < lower) | (times > upper)]
                pct = len(out) / len(times) * 100
            outlier_rows.append({"KEM": kem, "Platform": plat, "Outliers%": pct})

    outliers_df = pd.DataFrame(outlier_rows)
    out_pct = (
        outliers_df
        .pivot(index='KEM', columns='Platform', values='Outliers%')
        .rename(columns={'ARM': 'Outliers%_ARM', 'x86': 'Outliers%_x86'})
    )
    comparisons_df = comparisons_df.merge(out_pct, left_on='KEM', right_index=True)

    # --- Impresión del resumen -----------------------------------------------
    cols = [
        "KEM",
        "Mean_ARM", "SD_ARM", "Median_ARM", "IQR_ARM", "CV_ARM", "Outliers%_ARM",
        "Mean_x86", "SD_x86", "Median_x86", "IQR_x86", "CV_x86", "Outliers%_x86",
        "SpeedUp"
    ]
    print("\n📊 ARM vs x86 resumen (sin extremos, con IQR-outliers + SD/Median/IQR):")
    print(comparisons_df[cols].round(4).to_string(index=False))

    # --- Export a LaTeX v4 (extendida con SD, Median, IQR) -------------------
    table_df = comparisons_df[cols].round(2).copy()
    table_df.columns = [
        "KEM",
        "ARM_Mean", "ARM_SD", "ARM_Median", "ARM_IQR", "ARM_CV", "ARM_OutPct",
        "x86_Mean", "x86_SD", "x86_Median", "x86_IQR", "x86_CV", "x86_OutPct",
        "SpeedUp"
    ]

    tex_path = f"./output/handshake_comparison_{base_name}_v4.tex"
    with open(tex_path, 'w') as f:
        f.write("\\begin{table*}[!ht]\n")
        f.write("\\centering\n")
        f.write("\\begin{tabular}{l|rrrrrr|rrrrrr|r}\n")
        f.write("\\toprule\n")
        f.write("& \\multicolumn{6}{c}{\\bfseries ARM} "
                "& \\multicolumn{6}{c}{\\bfseries x86} & \\\\\n")
        f.write("\\cmidrule(lr){2-7} \\cmidrule(lr){8-13}\n")
        f.write(
            "KEM & Mean & SD & Median & IQR & CV & Out.\\% "
            "& Mean & SD & Median & IQR & CV & Out.\\% & SpeedUp \\\\\n"
        )
        f.write("\\midrule\n")
        for _, r in table_df.iterrows():
            f.write(
                f"{r['KEM']} & "
                f"{r['ARM_Mean']:.2f} & {r['ARM_SD']:.2f} & {r['ARM_Median']:.2f} & {r['ARM_IQR']:.2f} & {r['ARM_CV']:.2f} & {r['ARM_OutPct']:.2f} & "
                f"{r['x86_Mean']:.2f} & {r['x86_SD']:.2f} & {r['x86_Median']:.2f} & {r['x86_IQR']:.2f} & {r['x86_CV']:.2f} & {r['x86_OutPct']:.2f} & "
                f"{r['SpeedUp']:.2f}× \\\\\n"
            )
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")
        f.write("\\end{table*}\n")

    print(f"✔ LaTeX v4 created {tex_path}")
    return df_all


def generate_violin_plot(df_all, base_name):
    q99 = df_all["Time (ms)"].quantile(0.99)
    df_filtered = df_all[df_all["Time (ms)"] <= q99]
    plt.figure(figsize=(14, 11))
    sns.set(style="whitegrid")
    ax = sns.violinplot(
        data=df_filtered,
        x="KEM",
        y="Time (ms)",
        hue="Platform",
        split=True,
        inner="quartile",
        linewidth=1.2,
        palette="Set2",
        cut=0,
        scale="width"
    )
    plt.title(f"Impact of KEM on Handshake Time ({base_name})", fontsize=26)
    plt.legend(title="Platform", loc="upper left", fontsize=24, title_fontsize=24, ncol=2)
    plt.xlabel("", fontsize=26)
    plt.xticks(fontsize=26)
    plt.yticks(fontsize=26)
    plt.ylabel("Handshake Time (ms)", fontsize=26)

    # Modifica las etiquetas del eje X según el patrón
    new_labels = []
    for label in ax.get_xticklabels():
        original_text = label.get_text()
        new_text = original_text.replace('_', '_\n')
        new_labels.append(new_text)

    ax.set_xticklabels(new_labels)
    plt.tight_layout()
    plt.savefig(f"./output/violin_{base_name}.svg")
    plt.savefig(f"./output/violin_{base_name}.pdf")
    print(f"📁 Plot saved as: violin_{base_name}.*")
    plt.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python analyze_levels_Platforms_v2.py <csv_arm> <csv_x86>")
        sys.exit(1)

    csv_arm, csv_x86 = sys.argv[1], sys.argv[2]

    # Check filename conventions
    if "_arm" not in csv_arm.lower() or "_x86" not in csv_x86.lower():
        print("❌ Error: expected filenames like <sig>_tls_arm.csv and <sig>_tls_x86.csv")
        sys.exit(1)

    # Extract and compare base signature name
    sig1 = os.path.basename(csv_arm).split("_tls_")[0]
    sig2 = os.path.basename(csv_x86).split("_tls_")[0]
    if sig1 != sig2:
        print(f"❌ Mismatch: signatures differ ({sig1} vs {sig2})")
        sys.exit(1)

    base_name = sig1
    print(f"✅ Signature algorithm: {base_name}")
    print(f"🖥️  Comparing ARM ({csv_arm}) vs x86 ({csv_x86})")

    df_all = analyze_signature_csvs(csv_arm, csv_x86, base_name)
    print(f"\n📊 Loaded {len(df_all)} samples. Filtering extreme outliers...")
    generate_violin_plot(df_all, base_name)
