/******************************************************************************
*******************************************************************************
**
**  Copyright (C) Sistina Software, Inc.  1997-2003  All rights reserved.
**  Copyright (C) 2004 Red Hat, Inc.  All rights reserved.
**
**  This copyrighted material is made available to anyone wishing to use,
**  modify, copy, or redistribute it subject to the terms and conditions
**  of the GNU General Public License v.2.
**
*******************************************************************************
******************************************************************************/

#include "dlm_internal.h"
#include "config.h"

/* Config file defaults */
#define DEFAULT_TCP_PORT       21064
#define DEFAULT_LOCK_TIMEOUT      30
#define DEFAULT_BUFFER_SIZE     4096
#define DEFAULT_RSBTBL_SIZE      256
#define DEFAULT_LKBTBL_SIZE     1024
#define DEFAULT_DIRTBL_SIZE      512
#define DEFAULT_CONN_INCREMENT    32
#define DEFAULT_DEADLOCKTIME      10
#define DEFAULT_RECOVER_TIMER      5

struct dlm_config_info dlm_config = {
	.tcp_port = DEFAULT_TCP_PORT,
	.lock_timeout = DEFAULT_LOCK_TIMEOUT,
	.buffer_size = DEFAULT_BUFFER_SIZE,
	.rsbtbl_size = DEFAULT_RSBTBL_SIZE,
	.lkbtbl_size = DEFAULT_LKBTBL_SIZE,
	.dirtbl_size = DEFAULT_DIRTBL_SIZE,
	.conn_increment = DEFAULT_CONN_INCREMENT,
	.deadlocktime = DEFAULT_DEADLOCKTIME,
	.recover_timer = DEFAULT_RECOVER_TIMER
};

int dlm_config_init(void)
{
	/* FIXME: hook the config values into sysfs */
	return 0;
}

void dlm_config_exit(void)
{
}
