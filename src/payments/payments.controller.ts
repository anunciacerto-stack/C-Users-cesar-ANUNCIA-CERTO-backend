import { Controller, Get, Post, Body, Param, HttpCode, HttpStatus } from '@nestjs/common';
import { PaymentsService } from './payments.service';
import { IsNotEmpty, IsNumber, IsString, IsEmail, IsOptional } from 'class-validator';

export class CreatePixPaymentDto {
  @IsString()
  @IsNotEmpty()
  userId: string;

  @IsNumber()
  @IsNotEmpty()
  amount: number;

  @IsEmail()
  @IsNotEmpty()
  email: string;

  @IsString()
  @IsNotEmpty()
  cpf: string;

  @IsString()
  @IsOptional()
  type?: string;
}

@Controller('payments')
export class PaymentsController {
  constructor(private readonly paymentsService: PaymentsService) {}

  @Post('pix')
  async createPix(@Body() dto: CreatePixPaymentDto) {
    console.log('[POST /payments/pix] Gerando pagamento PIX para:', dto.userId);
    return this.paymentsService.createPixPayment(
      dto.userId,
      dto.amount,
      dto.email,
      dto.cpf,
      dto.type || 'subscription',
    );
  }

  @Get('status/:id')
  async getStatus(@Param('id') id: string) {
    console.log(`[GET /payments/status/${id}] Consultando status`);
    return this.paymentsService.getPaymentStatus(id);
  }

  @Post('webhook')
  @HttpCode(HttpStatus.OK)
  async handleWebhook(@Body() body: any) {
    return this.paymentsService.handleWebhook(body);
  }
}
