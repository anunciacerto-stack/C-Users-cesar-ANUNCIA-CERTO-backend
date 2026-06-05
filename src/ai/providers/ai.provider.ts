import { Injectable, ServiceUnavailableException } from '@nestjs/common';
import {
  AI_ASSISTANT_SCOPE,
  AI_DEFAULT_MODEL,
  AI_EXPLANATIONS,
  AI_HEURISTIC_RULES,
  type AiRule,
} from '../constants/ai-prompts';
import { AiAssistDto } from '../dto/ai-assist.dto';
import { AiExplainDto } from '../dto/ai-explain.dto';
import { AiSearchDto } from '../dto/ai-search.dto';

export interface AiAssistResult {
  suggestedTitle: string;
  suggestedDescription: string;
  suggestedCategory: string;
  suggestedSubcategory: string;
  suggestedTipoEntrada: string;
  tags: string[];
  confidence: number;
  notes: string[];
}

export interface AiSearchResult {
  intent: string;
  suggestedCategory: string;
  suggestedSubcategory: string;
  suggestedTipoEntrada: string;
  keywords: string[];
  notes: string[];
}

export interface AiExplainResult {
  title: string;
  explanation: string;
  steps: string[];
}

export interface AiProvider {
  assist(input: AiAssistDto): Promise<AiAssistResult>;
  search(input: AiSearchDto): Promise<AiSearchResult>;
  explain(input: AiExplainDto): Promise<AiExplainResult>;
}

type HeuristicMatch = AiRule & { matchedKeywords: string[] };

@Injectable()
export class MockAiProvider implements AiProvider {
  async assist(input: AiAssistDto): Promise<AiAssistResult> {
    const sourceText = normalizeText(
      [input.context, input.title, input.description, input.category, input.subcategory, input.tipoEntrada]
        .filter(Boolean)
        .join(' '),
    );
    const match = findBestRule(sourceText);
    const location = formatLocation(input.city, input.state);

    const fallbackCategory = cleanLabel(input.category) || 'geral';
    const fallbackSubcategory = cleanLabel(input.subcategory) || 'geral';
    const fallbackTipoEntrada = cleanLabel(input.tipoEntrada) || 'popular';

    const suggestedTitle = buildSuggestedTitle(input.title, match, input.city, input.state);
    const suggestedDescription = buildSuggestedDescription(input.description, match, location, input.context);

    return {
      suggestedTitle,
      suggestedDescription,
      suggestedCategory: match?.category ?? fallbackCategory,
      suggestedSubcategory: match?.subcategory ?? fallbackSubcategory,
      suggestedTipoEntrada: match?.tipoEntrada ?? fallbackTipoEntrada,
      tags: buildTags(input, match),
      confidence: clampConfidence(match?.confidence ?? inferFallbackConfidence(input)),
      notes: buildAssistNotes(input, match, location),
    };
  }

  async search(input: AiSearchDto): Promise<AiSearchResult> {
    const normalized = normalizeText([input.query, input.context].filter(Boolean).join(' '));
    const match = findBestRule(normalized);
    const keywords = extractKeywords(input.query, match);

    return {
      intent: buildIntent(input.query, input.context, match),
      suggestedCategory: match?.category ?? 'geral',
      suggestedSubcategory: match?.subcategory ?? 'consulta',
      suggestedTipoEntrada: match?.tipoEntrada ?? 'popular',
      keywords,
      notes: buildSearchNotes(input.context, match, keywords),
    };
  }

  async explain(input: AiExplainDto): Promise<AiExplainResult> {
    const topicKey = normalizeText(input.topic);
    const content = AI_EXPLANATIONS[topicKey] ?? AI_EXPLANATIONS.default;

    return {
      title: content.title,
      explanation: input.context
        ? `${content.explanation} Contexto atual: ${toSentenceCase(input.context)}.`
        : content.explanation,
      steps: content.steps,
    };
  }
}

@Injectable()
export class UnsupportedAiProvider implements AiProvider {
  constructor(private readonly providerName: string) {}

  async assist(_: AiAssistDto): Promise<AiAssistResult> {
    throw this.buildException();
  }

  async search(_: AiSearchDto): Promise<AiSearchResult> {
    throw this.buildException();
  }

  async explain(_: AiExplainDto): Promise<AiExplainResult> {
    throw this.buildException();
  }

  private buildException() {
    return new ServiceUnavailableException(
      `AI provider "${this.providerName}" ainda nao esta configurado para uso neste ambiente. Defina AI_PROVIDER=mock ou implemente o provider real com AI_BASE_URL, AI_MODEL e AI_API_KEY quando necessario.`,
    );
  }
}

export function createAiProvider(): AiProvider {
  const provider = (process.env.AI_PROVIDER ?? 'mock').trim().toLowerCase();
  const model = (process.env.AI_MODEL ?? AI_DEFAULT_MODEL).trim();

  switch (provider) {
    case 'mock':
    case 'local':
      return new MockAiProvider();
    case 'openai':
    case 'ollama':
      validateProviderReadiness(provider, model);
      return new UnsupportedAiProvider(provider);
    default:
      return new UnsupportedAiProvider(provider || 'desconhecido');
  }
}

function validateProviderReadiness(provider: string, model: string) {
  if (!model) {
    throw new ServiceUnavailableException(`AI provider "${provider}" requer AI_MODEL configurado antes do uso.`);
  }
}

function findBestRule(source: string): HeuristicMatch | null {
  if (!source) {
    return null;
  }

  let bestMatch: HeuristicMatch | null = null;

  for (const rule of AI_HEURISTIC_RULES) {
    const matchedKeywords = rule.keywords.filter((keyword) => source.includes(normalizeText(keyword)));
    if (matchedKeywords.length === 0) {
      continue;
    }

    const boostedConfidence = clampConfidence(rule.confidence + (matchedKeywords.length - 1) * 0.03);
    const currentMatch: HeuristicMatch = {
      ...rule,
      matchedKeywords,
      confidence: boostedConfidence,
    };

    if (!bestMatch || currentMatch.confidence > bestMatch.confidence) {
      bestMatch = currentMatch;
    }
  }

  return bestMatch;
}

function buildSuggestedTitle(
  title: string | undefined,
  match: HeuristicMatch | null,
  city?: string,
  state?: string,
) {
  const cleanedTitle = cleanLabel(title);
  const baseTitle = cleanedTitle || buildFallbackTitle(match);
  const location = formatLocation(city, state);
  const withCommercialTone = enrichTitle(baseTitle, match);
  return location && !withCommercialTone.toLowerCase().includes(location.toLowerCase())
    ? `${withCommercialTone} em ${location}`
    : withCommercialTone;
}

function buildSuggestedDescription(
  description: string | undefined,
  match: HeuristicMatch | null,
  location: string,
  context?: string,
) {
  const cleanedDescription = cleanText(description);
  const baseDescription =
    cleanedDescription ||
    `Anuncio com foco em ${match?.subcategory ?? 'divulgacao'} na plataforma ANUNCIA CERTO.`;

  const sentences = [toSentenceCase(baseDescription)];
  if (location) {
    sentences.push(`Disponivel em ${location}.`);
  }
  if (context) {
    sentences.push(`Contexto de uso: ${context.trim()}.`);
  }
  if (match?.category) {
    sentences.push(`Sugestao de enquadramento: ${match.category} / ${match.subcategory}.`);
  }
  return sentences.join(' ');
}

function buildTags(input: AiAssistDto, match: HeuristicMatch | null) {
  const tags = new Set<string>();

  for (const value of [input.title, input.description, input.city, input.state]) {
    for (const token of tokenize(value)) {
      if (token.length >= 3) {
        tags.add(token);
      }
      if (tags.size >= 5) {
        break;
      }
    }
    if (tags.size >= 5) {
      break;
    }
  }

  for (const tag of match?.tags ?? []) {
    tags.add(tag);
  }

  return Array.from(tags).slice(0, 6);
}

function buildAssistNotes(input: AiAssistDto, match: HeuristicMatch | null, location: string) {
  const notes = new Set<string>();
  notes.add(AI_ASSISTANT_SCOPE);

  if (match) {
    for (const note of match.notes) {
      notes.add(note);
    }
  } else {
    notes.add('Heuristica sem correspondencia forte; revise categoria e tipo manualmente.');
  }

  if (location) {
    notes.add(`Local identificado: ${location}.`);
  }

  if (!input.title || !input.description) {
    notes.add('Quanto mais detalhes forem enviados, melhores ficam as sugestoes.');
  }

  return Array.from(notes).slice(0, 4);
}

function buildIntent(query: string, context?: string, match?: HeuristicMatch | null) {
  const normalized = normalizeText(query);

  if (normalized.includes('anunciar') || normalized.includes('cadastro') || normalized.includes('cadastrar')) {
    return 'apoio_ao_cadastro';
  }
  if (normalized.includes('buscar') || normalized.includes('procur') || normalized.includes('consult')) {
    return 'consulta_assistida';
  }
  if (match?.category === 'empresas' || context === 'marketplace') {
    return 'classificacao_de_negocio';
  }
  return 'orientacao_geral';
}

function buildSearchNotes(context: string | undefined, match: HeuristicMatch | null, keywords: string[]) {
  const notes = new Set<string>();
  notes.add('Resposta apenas sugestiva; nenhuma acao foi executada automaticamente.');

  if (context) {
    notes.add(`Contexto considerado: ${context.trim()}.`);
  }

  if (match) {
    notes.add(`Melhor correspondencia heuristica: ${match.category} / ${match.subcategory}.`);
  } else {
    notes.add('Sem correspondencia forte; refine a consulta para obter sugestoes mais precisas.');
  }

  if (keywords.length > 0) {
    notes.add(`Palavras-chave extraidas: ${keywords.join(', ')}.`);
  }

  return Array.from(notes).slice(0, 4);
}

function extractKeywords(query: string, match: HeuristicMatch | null) {
  const keywords = new Set<string>();
  for (const token of tokenize(query)) {
    if (token.length >= 4) {
      keywords.add(token);
    }
    if (keywords.size >= 5) {
      break;
    }
  }

  for (const token of match?.matchedKeywords ?? []) {
    keywords.add(token);
  }

  return Array.from(keywords).slice(0, 6);
}

function inferFallbackConfidence(input: AiAssistDto) {
  let score = 0.35;
  if (input.title) score += 0.15;
  if (input.description) score += 0.15;
  if (input.city || input.state) score += 0.1;
  return score;
}

function buildFallbackTitle(match: HeuristicMatch | null) {
  if (match) {
    return toSentenceCase(`${match.subcategory} em destaque`);
  }
  return 'Anuncio em destaque';
}

function enrichTitle(title: string, match: HeuristicMatch | null) {
  const normalized = normalizeText(title);
  if (normalized.startsWith('vendo ')) {
    return toSentenceCase(title);
  }
  if (match?.category === 'servicos') {
    return toSentenceCase(`${title} com atendimento profissional`);
  }
  if (match?.category === 'lotes') {
    return toSentenceCase(`${title} com oportunidade comercial`);
  }
  return toSentenceCase(title);
}

function formatLocation(city?: string, state?: string) {
  const cleanedCity = cleanLabel(city);
  const cleanedState = cleanLabel(state)?.toUpperCase();
  if (cleanedCity && cleanedState) {
    return `${cleanedCity} - ${cleanedState}`;
  }
  return cleanedCity || cleanedState || '';
}

function cleanLabel(value?: string) {
  if (!value) {
    return '';
  }
  return toSentenceCase(
    value
      .trim()
      .replace(/\s+/g, ' ')
      .replace(/[^\p{L}\p{N}\s/-]/gu, ''),
  );
}

function cleanText(value?: string) {
  if (!value) {
    return '';
  }
  return value.trim().replace(/\s+/g, ' ').replace(/[^\p{L}\p{N}\s,./-]/gu, '');
}

function tokenize(value?: string) {
  return normalizeText(value)
    .split(/\s+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function normalizeText(value?: string) {
  return (value ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

function clampConfidence(value: number) {
  return Math.max(0, Math.min(1, Number(value.toFixed(2))));
}

function toSentenceCase(value: string) {
  return value
    .toLowerCase()
    .split(' ')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}
