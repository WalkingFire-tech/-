from core.dialogue.scene_perceiver import ScenePerceiver
p = ScenePerceiver()
r = p.perceive('这对么？')
print(f'主角色: {r.primary_role.value}')
print(f'次要角色: {[x.value for x in r.secondary_roles]}')
print(f'匹配指示词: {r.indicators_matched}')
print(f'角色分数:')
for k, v in r.role_scores.items():
    if v > 0:
        print(f'  {k.value}: {v:.2f}')
