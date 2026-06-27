from core.services.intent_parser import intent_parser
intent = intent_parser.parse('为什么会有冰雹？')
print(f'意图类型: {intent.type}')
print(f'置信度: {intent.confidence}')