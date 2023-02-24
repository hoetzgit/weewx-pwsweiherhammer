schema = [
    ('dateTime', 'INTEGER NOT NULL PRIMARY KEY'),
    ('usUnits', 'INTEGER NOT NULL'),
    ('interval', 'INTEGER NOT NULL'),
    ('mem_total', 'INTEGER'),
    ('mem_free', 'INTEGER'),
    ('mem_available', 'INTEGER'),
    ('mem_used', 'INTEGER'),
    ('swap_total', 'INTEGER'),
    ('swap_free', 'INTEGER'),
    ('swap_used', 'INTEGER'),
    ('cpu_user', 'INTEGER'),
    ('cpu_nice', 'INTEGER'),
    ('cpu_system', 'INTEGER'),
    ('cpu_idle', 'INTEGER'),
    ('cpu_iowait', 'INTEGER'),
    ('cpu_irq', 'INTEGER'),
    ('cpu_softirq', 'INTEGER'),
    ('load1', 'REAL'),
    ('load5', 'REAL'),
    ('load15', 'REAL'),
    ('proc_active', 'INTEGER'),
    ('proc_total', 'INTEGER'),

# measure cpu temperature (not all platforms support this)
    ('cpu_temp', 'REAL'),  # degree C
    ('cpu_temp1', 'REAL'), # degree C
    ('cpu_temp2', 'REAL'), # degree C
    ('cpu_temp3', 'REAL'), # degree C
    ('cpu_temp4', 'REAL'), # degree C

# measure rpi attributes (not all platforms support this)
    ('core_temp','REAL'), # degree C
    ('core_volt', 'REAL'),
    ('core_sdram_c', 'REAL'),
    ('core_sdram_i', 'REAL'),
    ('core_sdram_p', 'REAL'),
    ('arm_mem', 'REAL'),
    ('gpu_mem', 'REAL'),

# the default interface on most linux systems is eth0
    ('net_eth0_rbytes', 'INTEGER'),
    ('net_eth0_rpackets', 'INTEGER'),
    ('net_eth0_rerrs', 'INTEGER'),
    ('net_eth0_rdrop', 'INTEGER'),
    ('net_eth0_tbytes', 'INTEGER'),
    ('net_eth0_tpackets', 'INTEGER'),
    ('net_eth0_terrs', 'INTEGER'),
    ('net_eth0_tdrop', 'INTEGER'),

#    ('net_eth1_rbytes', 'INTEGER'),
#    ('net_eth1_rpackets', 'INTEGER'),
#    ('net_eth1_rerrs', 'INTEGER'),
#    ('net_eth1_rdrop', 'INTEGER'),
#    ('net_eth1_tbytes', 'INTEGER'),
#    ('net_eth1_tpackets', 'INTEGER'),
#    ('net_eth1_terrs', 'INTEGER'),
#    ('net_eth1_tdrop', 'INTEGER'),

# the default interface on most ubuntu systems is ens160
    ('net_ens160_rbytes', 'INTEGER'),
    ('net_ens160_rpackets', 'INTEGER'),
    ('net_ens160_rerrs', 'INTEGER'),
    ('net_ens160_rdrop', 'INTEGER'),
    ('net_ens160_tbytes', 'INTEGER'),
    ('net_ens160_tpackets', 'INTEGER'),
    ('net_ens160_terrs', 'INTEGER'),
    ('net_ens160_tdrop', 'INTEGER'),

# some systems have a wireless interface as wlan0
    ('net_wlan0_rbytes', 'INTEGER'),
    ('net_wlan0_rpackets', 'INTEGER'),
    ('net_wlan0_rerrs', 'INTEGER'),
    ('net_wlan0_rdrop', 'INTEGER'),
    ('net_wlan0_tbytes', 'INTEGER'),
    ('net_wlan0_tpackets', 'INTEGER'),
    ('net_wlan0_terrs', 'INTEGER'),
    ('net_wlan0_tdrop', 'INTEGER'),

# if the computer is an openvpn server, track the tunnel traffic
    ('net_tun0_rbytes', 'INTEGER'),
    ('net_tun0_rpackets', 'INTEGER'),
    ('net_tun0_rerrs', 'INTEGER'),
    ('net_tun0_rdrop', 'INTEGER'),
    ('net_tun0_tbytes', 'INTEGER'),
    ('net_tun0_tpackets', 'INTEGER'),
    ('net_tun0_terrs', 'INTEGER'),
    ('net_tun0_tdrop', 'INTEGER'),

# if the computer is an wireguard server, track the tunnel traffic
    ('net_wg0_rbytes', 'INTEGER'),
    ('net_wg0_rpackets', 'INTEGER'),
    ('net_wg0_rerrs', 'INTEGER'),
    ('net_wg0_rdrop', 'INTEGER'),
    ('net_wg0_tbytes', 'INTEGER'),
    ('net_wg0_tpackets', 'INTEGER'),
    ('net_wg0_terrs', 'INTEGER'),
    ('net_wg0_tdrop', 'INTEGER'),

# disk volumes will vary, but root is always present
    ('disk_root_total', 'INTEGER'),
    ('disk_root_free', 'INTEGER'),
    ('disk_root_used', 'INTEGER'),
# separate partition for home is not uncommon
    ('disk_home_total', 'INTEGER'),
    ('disk_home_free', 'INTEGER'),
    ('disk_home_used', 'INTEGER'),

# measure the ups parameters if we can
#    ('ups_temp', 'REAL'),    # degree C
#    ('ups_load', 'REAL'),    # percent
#    ('ups_charge', 'REAL'),  # percent
#    ('ups_voltage', 'REAL'), # volt
#    ('ups_time', 'REAL'),    # seconds
    ]