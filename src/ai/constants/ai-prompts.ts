export const AI_PROVIDER_TOKEN = 'AI_PROVIDER_TOKEN';

export const AI_DEFAULT_MODEL = 'anuncia-certo-assistant';

export const AI_ASSISTANT_SCOPE =
  'Assistente da plataforma ANUNCIA CERTO. Seja extremamente ágil, conciso, objetivo, direto e preciso na sua orientação em toda a plataforma. Responda rapidamente e de forma clara, sem rodeios. Seu papel é sugerir, nunca executar ações ou gravar dados.';

export const AI_EXPLANATIONS: Record<
  string,
  {
    title: string;
    explanation: string;
    steps: string[];
  }
> = {
  nfc: {
    title: 'Como o NFC ajuda na plataforma',
    explanation:
      'O NFC permite aproximar um dispositivo compativel para abrir informacoes do anuncio ou item com mais contexto e rapidez.',
    steps: [
      'Cadastre o item ou anuncio na plataforma.',
      'Associe o recurso NFC quando essa etapa estiver disponivel no fluxo.',
      'Use a aproximacao para exibir informacoes com seguranca e contexto ao usuario.',
    ],
  },
  qr: {
    title: 'Como o QR pode ser usado',
    explanation:
      'O QR facilita o acesso rapido a um anuncio, item ou perfil da plataforma sem exigir digitacao manual.',
    steps: [
      'Finalize o cadastro do conteudo na plataforma.',
      'Gere ou vincule o QR ao registro desejado.',
      'Compartilhe o QR para abrir o contexto correto no app ou painel.',
    ],
  },
  marketplace: {
    title: 'Como a IA apoia o marketplace',
    explanation:
      'A IA sugere categoria, melhora texto e identifica a intencao do usuario para agilizar cadastros e consultas sem alterar dados automaticamente.',
    steps: [
      'Envie titulo, descricao e contexto para a rota de assistencia.',
      'Revise as sugestoes retornadas em JSON.',
      'Aplique manualmente apenas o que fizer sentido para o anuncio.',
    ],
  },
  supermercados: {
    title: 'Rede Supermercados NFC',
    explanation:
      'A Rede Supermercados permite que mercadorias de gôndolas físicas sejam consultadas no app/site através de Tags NFC. Cada filiado possui dados e valores separados.',
    steps: [
      'Aproxime o celular na gôndola para registrar a visita NFC.',
      'Cadastre produtos sob os planos Bronze (Grátis), Prata (R$5,00) ou Ouro (R$10,00).',
      'Acumule pontos de fidelidade diretamente na balança ou caixa física.',
    ],
  },
  sorveterias: {
    title: 'Rede Sorveterias NFC & Fidelidade',
    explanation:
      'A Rede Sorveterias opera cardápios digitais interativos e programas de fidelidade via NFC. Usuários ganham pontos a cada pedido.',
    steps: [
      'Escolha um sabor premium (ex: Chocolate Belga) no cardápio.',
      'Aproxime a tag NFC para ganhar pontos de fidelidade instantaneamente.',
      'Resgate recompensas físicas ao atingir metas de pontos (ex: 200 pontos).',
    ],
  },
  oficinas: {
    title: 'Rede Oficinas & Ordens de Serviço',
    explanation:
      'O módulo Rede Oficinas gerencia Ordens de Serviço (OS) vinculadas a placas de veículos e tags NFC físicas de rastreio, oferecendo transparência total.',
    steps: [
      'Abra uma Ordem de Serviço informando placa, veículo e mecânico.',
      'Acompanhe o status (Aguardando, Em Andamento, Concluído) no painel.',
      'Use a tag NFC no para-brisa para que o cliente consulte o status atual do reparo.',
    ],
  },
  formaturas: {
    title: 'Módulo Formaturas & Venda de Fotos',
    explanation:
      'O módulo Formaturas conecta fotógrafos e estudantes, permitindo a seleção de fotos com marcas d’água (watermark), geração de álbuns digitais/físicos e contratos dinâmicos.',
    steps: [
      'O fotógrafo cria o evento de formatura e faz o upload das fotos com marca d’água.',
      'O formando visualiza a galeria e escolhe fotos para o Álbum ou Pôster.',
      'O pagamento é feito via PIX, dividindo o valor (split) automaticamente entre a plataforma e o fotógrafo.',
    ],
  },
  sherif: {
    title: 'Sherif Antifraude & Robôs NFC',
    explanation:
      'O Sherif é a auditoria de segurança da plataforma. Ele utiliza "robôs" circulares (tags NFC redondas coladas nos veículos/itens) para atestar a veracidade de documentos e histórico de sinistros, prevenindo fraudes.',
    steps: [
      'Vincule um robô NFC (tag redonda) ao para-brisa do veículo cadastrado.',
      'O agente Sherif faz a vistoria física e envia o status (APPROVED, PENDING, REJECTED).',
      'Qualquer usuário pode encostar na tag para ver a ficha completa de auditoria livre de fraudes.',
    ],
  },
  redes: {
    title: 'Redes Franqueadas & Filiados',
    explanation:
      'Modelo de negócio que permite comercializar o app transformando em Redes (Supermercados, Sorveterias, Oficinas). Cada filiado (ex: Mercearia do Zé, Super Antonio) tem movimentos individuais, banco de dados isolado e valores separados.',
    steps: [
      'O dono do estabelecimento adquire uma licença e se filia à Rede.',
      'Associa tags NFC individuais nas suas gôndolas, balcões ou mesas.',
      'Recebe relatórios e valores de forma 100% isolada e exclusiva no subdomínio (ex: anunciacerto.com.br/superm).',
    ],
  },
  nfc_por_categoria: {
    title: 'Gravação NFC por Categoria',
    explanation:
      'Cada categoria possui regras de planos que habilitam o NFC: Bronze (2 fotos, sem NFC), Prata (6 fotos, painel básico) e Ouro (Fotos ilimitadas + NFC físico incluso).',
    steps: [
      'Escolha a categoria e o plano ideal do anúncio.',
      'Aprovado o pagamento, aproxime o celular da tag para gravar o link criptografado.',
      'Cole a tag no veículo, produto ou estabelecimento para ativação.',
    ],
  },
  default: {
    title: 'Como o assistente pode te ajudar',
    explanation:
      'Olá! Sou o assistente de voz da Anuncia Certo. Estou aqui para te apoiar de forma otimista e objetiva! Posso te orientar sobre como cadastrar veículos, usar tags NFC, configurar o mural de vendas ou realizar consultas rápidas.',
    steps: [
      'Pergunte sobre NFC, Planos Bronze/Prata/Ouro ou Redes Credenciadas.',
      'Toque na tela a qualquer momento para falar ou me interromper.',
      'Estou sempre à disposição para esclarecer suas dúvidas da melhor forma!',
    ],
  },
};

export type AiRule = {
  keywords: string[];
  category: string;
  subcategory: string;
  tipoEntrada: string;
  tags: string[];
  confidence: number;
  notes: string[];
};

export const AI_HEURISTIC_RULES: AiRule[] = [
  {
    keywords: ['manicure', 'unha', 'esmalte'],
    category: 'servicos',
    subcategory: 'manicure',
    tipoEntrada: 'popular',
    tags: ['beleza', 'manicure', 'esmalte'],
    confidence: 0.9,
    notes: ['Conteudo com foco em atendimento de beleza e cuidados com unhas.'],
  },
  {
    keywords: ['barbearia', 'barbeiro'],
    category: 'servicos',
    subcategory: 'barbearia',
    tipoEntrada: 'comercial',
    tags: ['barbearia', 'beleza', 'atendimento'],
    confidence: 0.9,
    notes: ['Conteudo identificado como servico de barbearia.'],
  },
  {
    keywords: ['lote', 'bezerro', 'gado'],
    category: 'lotes',
    subcategory: 'bezerro',
    tipoEntrada: 'rastreavel',
    tags: ['lote', 'gado', 'bezerro'],
    confidence: 0.96,
    notes: ['Conteudo com indicio de lote rural ou animal rastreavel.'],
  },
  {
    keywords: ['casa', 'apartamento', 'aluguel'],
    category: 'imoveis',
    subcategory: 'residencial',
    tipoEntrada: 'comercial',
    tags: ['imoveis', 'moradia', 'aluguel'],
    confidence: 0.88,
    notes: ['Conteudo com linguagem de oferta imobiliaria.'],
  },
  {
    keywords: ['carro', 'moto', 'veiculo', 'saude veicular'],
    category: 'veiculos',
    subcategory: 'automotores',
    tipoEntrada: 'comercial',
    tags: ['veiculos', 'mobilidade', 'anuncio', 'saude veicular'],
    confidence: 0.88,
    notes: ['Conteudo com indicio de anuncio de veiculo e saude veicular.'],
  },
  {
    keywords: ['pet', 'cachorro', 'gato'],
    category: 'animais',
    subcategory: 'pets',
    tipoEntrada: 'popular',
    tags: ['animais', 'pet', 'cuidados'],
    confidence: 0.86,
    notes: ['Conteudo relacionado a animais domesticos.'],
  },
  {
    keywords: ['loja', 'mercado', 'farmacia', 'supermercado', 'gondola'],
    category: 'supermercados',
    subcategory: 'gondola',
    tipoEntrada: 'comercial',
    tags: ['supermercados', 'comercio', 'vendas', 'gondola'],
    confidence: 0.9,
    notes: ['Conteudo relacionado à Rede Supermercados e gôndolas NFC.'],
  },
  {
    keywords: ['sorveteria', 'sorvete', 'gelateria', 'fidelidade', 'sabor'],
    category: 'sorveterias',
    subcategory: 'fidelidade',
    tipoEntrada: 'parceiro',
    tags: ['sorveterias', 'fidelidade', 'sabor', 'pontos'],
    confidence: 0.9,
    notes: ['Conteudo relacionado à Rede Sorveterias e programa de fidelidade NFC.'],
  },
  {
    keywords: ['oficina', 'mecanica', 'mecanico', 'ordem de servico', 'placa'],
    category: 'oficinas',
    subcategory: 'mecanica',
    tipoEntrada: 'parceiro',
    tags: ['oficinas', 'mecanica', 'servico', 'ordem de servico'],
    confidence: 0.92,
    notes: ['Conteudo relacionado à Rede Oficinas e Ordens de Serviço.'],
  },
  {
    keywords: ['sherif', 'antifraude', 'seguranca', 'auditoria', 'robo', 'sinistro'],
    category: 'sherif',
    subcategory: 'antifraude',
    tipoEntrada: 'rastreavel',
    tags: ['sherif', 'antifraude', 'auditoria', 'robo nfc'],
    confidence: 0.95,
    notes: ['Conteudo relacionado ao Sherif Antifraude e robôs NFC circulares.'],
  },
  {
    keywords: ['formatura', 'album', 'fotografo', 'fotos', 'poster'],
    category: 'formaturas',
    subcategory: 'album',
    tipoEntrada: 'comercial',
    tags: ['formaturas', 'album', 'fotografo', 'fotos'],
    confidence: 0.92,
    notes: ['Conteudo relacionado a Formaturas, fotos com marca d’água e split de pagamento.'],
  },
  {
    keywords: ['redes', 'franquia', 'filiado', 'licenca', 'antonio', 'ze', 'zelia'],
    category: 'redes',
    subcategory: 'franquias',
    tipoEntrada: 'parceiro',
    tags: ['redes', 'franquia', 'filiado', 'movimentos'],
    confidence: 0.95,
    notes: ['Conteudo relacionado a Redes Franqueadas com movimentos isolados por filiado.'],
  },
];
