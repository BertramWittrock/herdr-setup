// Set every key on the Razer keyboard from one frame of colours.
// Usage: razer-keys FRAME
//   FRAME is 6 rows x 22 columns of RRGGBB hex, row by row (792 hex characters).
// Built against librazermacos (GPL-2.0); see build.sh.
#include <stdio.h>
#include <string.h>
#include "razerdevice.h"
#include "razerkbd_driver.h"

#define ROWS 6
#define COLS 22

static int hex_value(char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

int main(int argc, const char *argv[])
{
    if (argc != 2 || strlen(argv[1]) != ROWS * COLS * 6)
    {
        fprintf(stderr, "usage: razer-keys FRAME  (%d rows x %d columns of RRGGBB)\n", ROWS, COLS);
        return 2;
    }

    // One custom-frame record per row: ROW_ID, START_COL, STOP_COL, then RGB for each column.
    char buf[ROWS * (3 + COLS * 3)];
    const char *hex = argv[1];
    int offset = 0;
    for (int row = 0; row < ROWS; row++)
    {
        buf[offset++] = row;
        buf[offset++] = 0;
        buf[offset++] = COLS - 1;
        for (int i = 0; i < COLS * 3; i++, hex += 2)
        {
            int high = hex_value(hex[0]), low = hex_value(hex[1]);
            if (high < 0 || low < 0)
            {
                fprintf(stderr, "razer-keys: FRAME must be hex\n");
                return 2;
            }
            buf[offset++] = (char)(high * 16 + low);
        }
    }

    IOUSBDeviceInterface **keyboard = getRazerUSBDeviceInterface(TYPE_KEYBOARD);
    if (keyboard == NULL)
    {
        fprintf(stderr, "razer-keys: no Razer keyboard found\n");
        return 1;
    }
    razer_attr_write_matrix_custom_frame(keyboard, buf, offset);
    razer_attr_write_mode_custom(keyboard, "1", 1);
    closeRazerUSBDeviceInterface(keyboard);
    return 0;
}
