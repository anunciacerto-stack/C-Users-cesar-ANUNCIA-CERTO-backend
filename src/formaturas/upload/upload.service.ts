import { Injectable, Logger } from '@nestjs/common';
import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';
// Instale 'sharp' no backend caso ainda não tenha (npm install sharp)
import * as sharp from 'sharp';

@Injectable()
export class FormaturasUploadService {
  private readonly logger = new Logger(FormaturasUploadService.name);
  
  // O Caminho absoluto e inviolável do servidor local
  private readonly BASE_STORAGE_DIR = 'D:\\AnunciaCerto_Storage\\Formaturas';

  constructor() {
    this.ensureStorageExists();
  }

  /**
   * Garante que a estrutura física do disco D: exista e esteja pronta para receber.
   */
  private ensureStorageExists() {
    if (!fs.existsSync(this.BASE_STORAGE_DIR)) {
      try {
        fs.mkdirSync(this.BASE_STORAGE_DIR, { recursive: true });
        this.logger.log(`Storage físico criado com sucesso: ${this.BASE_STORAGE_DIR}`);
      } catch (err) {
        this.logger.error(`FALHA CRÍTICA: Não foi possível acessar o disco D: em ${this.BASE_STORAGE_DIR}`, err);
      }
    }
  }

  /**
   * Processa o lote de upload vindo do Fotógrafo.
   * Cria pastas seguras, salva a Original (High-Res) e gera a miniatura (Watermark) instantaneamente.
   */
  async processBatchUpload(eventId: string, files: Express.Multer.File[]) {
    this.logger.log(`Iniciando processamento de ${files.length} fotos para o Evento: ${eventId}`);
    
    // Pastas do evento
    const eventDir = path.join(this.BASE_STORAGE_DIR, eventId);
    const highResDir = path.join(eventDir, 'high-res');
    const watermarkedDir = path.join(eventDir, 'watermarked');

    // Cria as pastas se não existirem
    [highResDir, watermarkedDir].forEach(dir => {
      if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    });

    const results = [];

    // Processa uma por uma aplicando compressão e marca d'água
    for (const file of files) {
      const fileId = crypto.randomUUID();
      const extension = path.extname(file.originalname) || '.jpg';
      
      const originalPath = path.join(highResDir, `${fileId}${extension}`);
      const watermarkedPath = path.join(watermarkedDir, `${fileId}_preview.jpg`);

      try {
        // 1. Salva a ORIGINAL segura no HD (NUNCA VAI PARA O FRONTEND DIRETO)
        fs.writeFileSync(originalPath, file.buffer);

        // 2. Cria a versão BLINDADA com Sharp (Baixa Resolução + Marca D'água)
        await this.applyWatermark(file.buffer, watermarkedPath);

        results.push({
          fileId,
          originalName: file.originalname,
          originalPath,
          watermarkedPath,
          status: 'success'
        });

      } catch (err) {
        this.logger.error(`Erro ao processar arquivo ${file.originalname}:`, err);
        results.push({ fileId, originalName: file.originalname, status: 'error' });
      }
    }

    return results;
  }

  /**
   * Pega o Buffer original e gera uma versão de baixa qualidade (WebP ou JPG)
   * embaçada/com logo, ideal para vitrine sem risco de roubo.
   */
  private async applyWatermark(inputBuffer: Buffer, outputPath: string) {
    try {
      // Cria uma imagem com um texto "ANUNCIA CERTO - COMPRA PENDENTE" (usando SVG gerado dinamicamente para sobrepor)
      const svgImage = `
      <svg width="800" height="600">
        <style>
          .title { fill: rgba(255, 255, 255, 0.4); font-size: 60px; font-weight: bold; font-family: Arial; }
        </style>
        <text x="50%" y="50%" text-anchor="middle" alignment-baseline="middle" class="title" transform="rotate(-45 400 300)">ANUNCIA CERTO</text>
      </svg>
      `;
      const svgBuffer = Buffer.from(svgImage);

      // Aplica Sharp para redimensionar (blur leve) + colocar o texto por cima
      await sharp(inputBuffer)
        .resize({ width: 800, withoutEnlargement: true }) // Reduz qualidade para web
        .jpeg({ quality: 60 }) // Qualidade mediana
        .composite([
          {
            input: svgBuffer,
            gravity: 'center'
          }
        ])
        .toFile(outputPath);
    } catch (err) {
      this.logger.error('Erro na geração de marca dágua:', err);
      // Se falhar a marca d'água super chique, salva só borrado e pequeno
      await sharp(inputBuffer)
        .resize(500)
        .blur(3)
        .toFile(outputPath);
    }
  }
}
