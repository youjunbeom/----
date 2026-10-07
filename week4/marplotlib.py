import matplotlib.pyplot as plt
plt.plot(data["time_s"], data["stress_MPa"], marker="o")
plt.xlabel("Time (s)")
plt.ylabel("Stress (MPa)")
plt.savefig("stress_plot.png", dpi=150)