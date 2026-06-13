import { Controller, Post, UseInterceptors, UploadedFile, Param, Body } from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { FormaturasService } from './formaturas.service';

@Controller('formaturas')
export class FormaturasController {
  constructor(private readonly formaturasService: FormaturasService) {}

  @Post('upload/:alunoId')
  @UseInterceptors(FileInterceptor('foto')) // Espera um form-data com a chave 'foto'
  async uploadFoto(
    @Param('alunoId') alunoId: string, // UUID do aluno (vindo do Prisma)
    @UploadedFile() file: Express.Multer.File,
  ) {
    if (!file) {
      return { sucesso: false, mensagem: 'Nenhum arquivo enviado.' };
    }
    
    // Chama o serviço que vai salvar a foto no disco D: e gerar o Preview
    return this.formaturasService.uploadFoto(alunoId, file);
  }

  @Post('checkout/:alunoId')
  async checkoutSplit(
    @Param('alunoId') alunoId: string,
    @Body() body: { fotografoToken: string; valorTotal: number }
  ) {
    const { fotografoToken, valorTotal } = body;
    if (!fotografoToken || !valorTotal) {
      return { sucesso: false, mensagem: 'Dados inválidos para o checkout.' };
    }

    return this.formaturasService.criarPagamentoSplit(alunoId, fotografoToken, valorTotal);
  }
}

