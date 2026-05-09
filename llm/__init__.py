"""LLM 层统一出口。"""
from .world_gen import generate_initial_population, generate_birth
from .action import get_action_result
from .autonomy import generate_npc_autonomy
from .divine import (generate_prayer_response, generate_divine_gaze,
                     generate_life_snapshot, generate_oracle_query,
                     generate_yearly_digest)
from .codegen import (check_emergence, generate_module_code, fix_module_code,
                      upgrade_module_code, get_error_narrative,
                      get_fix_narrative, get_upgrade_narrative, MODULE_API_DOCS)
