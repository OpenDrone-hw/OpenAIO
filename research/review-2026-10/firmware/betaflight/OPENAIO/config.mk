# OpenAIO: make-level flash settings for the RP2354A (2 MB in-package W25Q16JVWI).
#
# Upstream mechanism (betaflight/betaflight 4dea42a9):
#   - mk/config.mk:50-51 includes $(CONFIG_PATH)/config.mk when it exists.
#   - src/platform/PICO/target/common/target_RP2350.mk:1-10 defaults MCU_FLASH_SIZE = 8192 and
#     PICO_FLASH_SIZE_BYTES = 8388608, and says both can be overridden here.
#   - Makefile:296-304 uses TARGET_FLASH_SIZE (KB) for -DTARGET_FLASH_SIZE.
# Format copied from betaflight/config e1d87e7e configs/RASP/RASPBERRY_PI_UAVFC/config.mk (4 MB board),
# with the sizes changed to 2 MB. The linker layout is set by pico_flash_mem.ld in this folder.

# Override MCU_FLASH_SIZE (KB)
TARGET_FLASH_SIZE = 2048

# For pico-sdk, define flash-related attributes
# 2097152 = 2 * 1024 * 1024
# CLKDIV 2 and the W25Q080 boot2 choice are unchanged from the upstream default and the UAVFC config.
PICO_FLASH_DEFINES = \
                   -DPICO_FLASH_SPI_CLKDIV=2 \
                   -DPICO_FLASH_SIZE_BYTES=2097152 \
                   -DPICO_BOOT_STAGE2_CHOOSE_W25Q080=1
