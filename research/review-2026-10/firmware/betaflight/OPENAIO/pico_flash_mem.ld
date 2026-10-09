/*
 * OpenAIO: RP2354A has 2 MB of in-package flash (W25Q16JVWI die, RP2350.pdf p14 and p1331).
 *
 * Upstream mechanism: when pico_flash_mem.ld is present in the config folder, the build uses it
 * instead of src/platform/PICO/link/pico_flash_mem_defaults.ld
 * (betaflight/betaflight 4dea42a9, src/platform/PICO/mk/RP2350.mk:506-516).
 * The two assignments below copy the format of betaflight/config e1d87e7e
 * configs/RASP/RASPBERRY_PI_UAVFC/pico_flash_mem.ld.
 *
 * Resulting layout (src/platform/PICO/link/pico_rp2350_memory.ld):
 *   FLASH        0x10000000  2M - 64K - 16K = 1968K  code (RUN_FROM_RAM copies most of it to SRAM)
 *   FLASH_CONFIG 0x101EC000  64K                     Betaflight settings
 *   FLASH_FONT   0x101FC000  16K                     FB OSD font (OSD_FB_PICO_FLASH_FONT)
 * Without this file, the default PRIMARY_FLASH_LENGTH = 4M places FLASH_CONFIG at 4 MB - 64 KB,
 * beyond the end of the 2 MB device.
 */

/* Set the size of the primary flash. */
PRIMARY_FLASH_LENGTH = 2M;

/* Set the size allocated to fonts (for FB_OSD). */
FONT_LENGTH = 16K;
