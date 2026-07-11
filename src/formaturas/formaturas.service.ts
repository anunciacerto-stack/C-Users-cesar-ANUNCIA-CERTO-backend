import { Injectable, InternalServerErrorException } from '@nestjs/common';
import * as fs from 'fs/promises';
import * as path from 'path';
import * as crypto from 'crypto';
import sharp from 'sharp'; // Sharp ativado para a marca d'água
import axios from 'axios';

@Injectable()
export class FormaturasService {
  private readonly baseDir = 'D:\\AnunciaCerto_Storage\\Formaturas';
  private readonly originaisDir = path.join(this.baseDir, 'Originais');
  private readonly previewsDir = path.join(this.baseDir, 'Previews');
  private readonly MP_ACCESS_TOKEN = process.env.MP_ACCESS_TOKEN || 'APP_USR-SEU_TOKEN_AQUI'; // Token do Anuncia Certo

  constructor() {
    this.ensureDirectories();
  }

  // Garante que as pastas no Disco D: existam ao iniciar o servidor
  private async ensureDirectories() {
    try {
      await fs.mkdir(this.originaisDir, { recursive: true });
      await fs.mkdir(this.previewsDir, { recursive: true });
      console.log(`[Formaturas] Pastas de armazenamento garantidas no disco D:`);
    } catch (error) {
      console.error('Erro ao criar pastas no disco D:', error);
    }
  }

  async uploadFoto(alunoId: string, file: Express.Multer.File) {
    try {
      // Gera um nome único para o arquivo
      const fileExt = path.extname(file.originalname);
      const fileName = `${alunoId}_${crypto.randomBytes(8).toString('hex')}${fileExt}`;
      
      const caminhoAltaRes = path.join(this.originaisDir, fileName);
      const caminhoPreview = path.join(this.previewsDir, `preview_${fileName}`);

      // 1. Salva a foto Original (Alta Resolução) no Disco D:
      await fs.writeFile(caminhoAltaRes, file.buffer);

      // 2. Gera o Preview protegido (Baixa Resolução / Tarja) no Disco D:
      await sharp(file.buffer)
        .resize(800)          // Reduz a resolução
        .blur(15)             // Aplica a tarja/blur anti-pirataria
        .toFile(caminhoPreview);
      
      // Retorna os dados que serão salvos no banco de dados (Prisma)
      return {
        sucesso: true,
        mensagem: 'Fotos processadas e salvas no disco D: com segurança.',
        dados: {
          alunoId,
          caminhoAltaRes,
          caminhoPreview
        }
      };
    } catch (error) {
      console.error(error);
      throw new InternalServerErrorException('Erro ao processar a foto.');
    }
  }

  async criarPagamentoSplit(alunoId: string, fotografoMpAccessToken: string, valorTotal: number) {
    try {
      // Cálculo do Split: 25% Anuncia Certo (Fee) / 75% Fotógrafo (Recebedor principal)
      const taxaAnunciaCerto = valorTotal * 0.25;

      const preferenceData = {
        items: [
          {
            title: 'Pacote de Fotos de Formatura',
            unit_price: valorTotal,
            quantity: 1,
            currency_id: 'BRL',
          }
        ],
        marketplace_fee: taxaAnunciaCerto, // Os 25% que ficam pra plataforma
        payer: {
          email: 'aluno_teste@example.com' // Idealmente puxado do BD
        },
        back_urls: {
          success: 'https://seusite.com.br/sucesso',
          failure: 'https://seusite.com.br/falha',
          pending: 'https://seusite.com.br/pendente'
        },
        auto_return: 'approved'
      };

      // Chamada para a API do Mercado Pago criando a preferência de checkout com Split
      // A requisição usa o token do FOTÓGRAFO (ele é o vendedor), mas cobra a marketplace_fee para a plataforma
      const response = await axios.post(
        'https://api.mercadopago.com/checkout/preferences',
        preferenceData,
        {
          headers: {
            'Authorization': `Bearer ${fotografoMpAccessToken}`,
            'Content-Type': 'application/json'
          }
        }
      );

      return {
        sucesso: true,
        urlPagamento: response.data.init_point, // Link para o aluno pagar
        preferenceId: response.data.id
      };
    } catch (error) {
      console.error('Erro no Mercado Pago:', error.response?.data || error.message);
      throw new InternalServerErrorException('Erro ao gerar pagamento com split.');
    }
  }
}

