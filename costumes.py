"""Validated wardrobe registry; all models are local runtime assets."""
COSTUMES = {
    'classic': {'label':'经典魔法师','folder':'megumin','full_body':False},
    'eyepatch': {'label':'经典眼罩','folder':'megumin-eyepatch','full_body':False},
    'schooluniform': {'label':'四星校服','folder':'megumin-schooluniform','full_body':False},
    'cafe': {'label':'咖啡厅','folder':'megumin-cafe','full_body':True},
    'ny': {'label':'新年和服','folder':'megumin-ny','full_body':True},
    'pj': {'label':'睡衣','folder':'megumin-pj','full_body':True},
}
def legacy_costume(settings):
    if settings.get('school_uniform',True): return 'schooluniform'
    return 'eyepatch' if settings.get('eyepatch',False) else 'classic'
