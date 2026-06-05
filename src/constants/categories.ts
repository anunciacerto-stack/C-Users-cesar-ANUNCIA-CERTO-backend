export const ENTRY_TYPES = ['popular', 'comercial', 'parceiro', 'rastreavel'] as const;

export const MAIN_CATEGORIES = [
  'servicos',
  'produtos',
  'empresas',
  'imoveis',
  'veiculos',
  'animais',
  'lotes',
  'objetos',
] as const;

export const SUBCATEGORIES_BY_MAIN: Record<(typeof MAIN_CATEGORIES)[number], string[]> = {
  servicos: ['manicure', 'barbearia', 'costura', 'mecanica', 'eletrica', 'limpeza'],
  produtos: ['roupas', 'calcados', 'eletronicos', 'alimentos'],
  empresas: ['loja', 'mercado', 'farmacia', 'oficina', 'escritorio'],
  imoveis: ['casa', 'apartamento', 'lote', 'chacara'],
  veiculos: ['carro', 'moto', 'caminhao', 'implemento'],
  animais: ['pet', 'gado', 'cavalo', 'aves'],
  lotes: ['leilao', 'bezerro', 'gado de corte', 'gado leiteiro'],
  objetos: ['chave', 'equipamento', 'ferramenta', 'documento'],
};

export const PLAN_OPTIONS = ['base', 'pro', 'premium'] as const;
export const STATUS_OPTIONS = ['ativo', 'pausado', 'arquivado'] as const;

export const DROPDOWN_FIELDS = ['estado', 'cidade', 'categoria', 'subcategoria', 'tipoEntrada', 'plano'] as const;
