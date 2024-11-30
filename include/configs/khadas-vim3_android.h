/* SPDX-License-Identifier: GPL-2.0+ */
/*
 * Configuration for the khadas VIM3 Android
 *
 * Copyright (C) 2021 Baylibre, SAS
 * Author: Guillaume LA ROQUE <glaroque@baylibre.com>
 */

#ifndef __CONFIG_H
#define __CONFIG_H

#define EXTRA_ANDROID_ENV_SETTINGS \
	"board=vim3\0" \
	"board_name=vim3\0" \

#include <configs/meson64_android.h>

#endif /* __CONFIG_H */
