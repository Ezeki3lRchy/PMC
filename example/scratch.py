import numpy as np

# 给定的流动参数
translational_temp = 300  # 平动温度, K
vibrational_temp = 4000  # 振动温度, K
velocity = 3700  # m/s

# 比热比和气体常数
gamma = 1.4  # 比热比, 空气在标准条件下
R = 287.05  # 空气的气体常数, J/(kg·K)

# 根据平动温度计算声速
sound_speed_translational = np.sqrt(gamma * R * translational_temp)

# 计算基于平动温度的马赫数
mach_number_translational = velocity / sound_speed_translational

# 如果需要，根据振动温度计算声速可能需要更复杂的模型，因为振动温度远高于平动温度
# 此处我们仅计算基于平动温度的声速和马赫数

print(f"Sound Speed (based on translational temperature): {sound_speed_translational} m/s")
print(f"Mach Number (based on translational temperature): {mach_number_translational}")