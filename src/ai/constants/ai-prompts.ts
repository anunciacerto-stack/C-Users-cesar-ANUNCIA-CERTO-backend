export const AI_PROVIDER_TOKEN = 'AI_PROVIDER_TOKEN';

export const AI_DEFAULT_MODEL = 'anuncia-certo-assistant';

export const AI_ASSISTANT_SCOPE =
  'Assistente da plataforma ANUNCIA CERTO. Seu papel e sugerir, nunca executar acoes ou gravar dados.';

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
  default: {
    title: 'Como a assistencia funciona',
    explanation:
      'A assistencia responde com sugestoes curtas e objetivas para orientar o uso da plataforma sem executar acoes automaticamente.',
    steps: [
      'Informe o contexto da sua necessidade.',
      'Analise as sugestoes retornadas pela IA.',
      'Confirme manualmente qualquer decisao antes de salvar no sistema.',
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
    keywords: ['carro', 'moto'],
    category: 'veiculos',
    subcategory: 'automotores',
    tipoEntrada: 'comercial',
    tags: ['veiculos', 'mobilidade', 'anuncio'],
    confidence: 0.88,
    notes: ['Conteudo com indicio de anuncio de veiculo.'],
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
    keywords: ['loja', 'mercado', 'farmacia'],
    category: 'empresas',
    subcategory: 'comercio',
    tipoEntrada: 'comercial',
    tags: ['empresa', 'comercio', 'vendas'],
    confidence: 0.87,
    notes: ['Conteudo com perfil de empresa ou ponto comercial.'],
  },
  {
    keywords: ['oficina', 'mecanica', 'mecanico'],
    category: 'servicos',
    subcategory: 'oficina',
    tipoEntrada: 'parceiro',
    tags: ['oficina', 'mecanica', 'servico'],
    confidence: 0.87,
    notes: ['Conteudo com foco em servico tecnico ou oficina.'],
  },
];
