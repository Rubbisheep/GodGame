"""LLM 层统一出口。"""
from .world_gen import generate_initial_population, generate_new_entity, generate_birth
from .action import get_action_result
from .autonomy import generate_npc_autonomy
from .mutations import generate_mutation_description, generate_spread_description
from .divine import (generate_prayer_response, generate_divine_gaze,
                     generate_other_god_event, generate_world_myth,
                     generate_life_snapshot, generate_npc_dialogue,
                     generate_oracle_query)
from .codegen import (check_emergence, generate_module_code, fix_module_code,
                      upgrade_module_code, get_error_narrative,
                      get_fix_narrative, get_upgrade_narrative, MODULE_API_DOCS)
