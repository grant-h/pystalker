# pystalker

A Python library to parse various files from the S.T.A.L.K.E.R series of games, including mods like Anomaly and GAMMA.

## Setup

You will need Python 3.X and pip.

```
git clone https://github.com/grant-h/pystalker
cd pystalker/
pip install -e .
pystalker --help
```

## pystalker CLI

pystalker comes with a command line LTX exploration tool. You can query the keys of different LTX objects as they would appear in-game at runtime.
It supports tab completion and some "bang" (!) commands for more advanced queries.

```
$ pystalker --path ~/anomaly/unpacked/
>
> wpn_ak10
Display all 100 possibilities? (y or n)
wpn_ak101                  wpn_ak101_camo             ...
> wpn_ak101.*
<LTXSection wpn_ak101, parents=4, keys=140, file=w_ak101.ltx>
use5_functor = ui_itm_details.menu_details
use5_action_functor = ui_itm_details.func_details
use5_modes = ['inventory', 'loot', 'trade', 'repair']
use5_containers = ['actor_bag', 'actor_equ', 'actor_belt', 'actor_trade', 'actor_trade_bag', 'npc_bag', 'npc_trade', 'npc_trade_bag']
use6_functor = item_parts.menu_disassembly
use6_action_functor = item_parts.func_disassembly
use6_modes = ['inventory', 'loot']
use6_containers = ['actor_bag', 'actor_equ', 'actor_belt', 'npc_bag']
use7_functor = ui_debug_launcher.menu_cond_inc
use7_action_functor = ui_debug_launcher.func_cond_inc
use8_functor = ui_debug_launcher.menu_cond_dec
use8_action_functor = ui_debug_launcher.func_cond_dec
use9_functor = ui_debug_launcher.menu_release
use9_action_functor = ui_debug_launcher.func_release
immunities_sect = sect_identity_immunities
slot = 2
description = st_wpn_ak101_descr // The AK-101 is an assault rifle of the Kalashnikov family designed for 
default_to_ruck = false
...
kill_msg_height = 28
> exit
$ 
```
