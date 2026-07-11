import { Injectable, HttpException, HttpStatus } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import * as crypto from 'crypto';

@Injectable()
export class PaymentsService {
  private readonly mpAccessToken = process.env.MERCADO_PAGO_ACCESS_TOKEN || 'TEST-8293948329384923-060617-5a2a2f232b2b2b2b2b2b2b2b2b2b2b2b-12345678';

  constructor(private readonly prisma: PrismaService) {}

  async createPixPayment(userId: string, amount: number, email: string, cpf: string, type = 'subscription') {
    // Valida o usuário
    const user = await this.prisma.user.findUnique({ where: { id: userId } });
    if (!user) {
      throw new HttpException('Usuário não encontrado', HttpStatus.NOT_FOUND);
    }

    const cleanCpf = cpf.replace(/\D/g, '');
    if (cleanCpf.length !== 11) {
      throw new HttpException('CPF inválido. Deve conter 11 dígitos.', HttpStatus.BAD_REQUEST);
    }

    const idempotencyKey = crypto.randomUUID();
    const url = 'https://api.mercadopago.com/v1/payments';

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.mpAccessToken}`,
          'Content-Type': 'application/json',
          'X-Idempotency-Key': idempotencyKey,
        },
        body: JSON.stringify({
          transaction_amount: amount,
          description: this.getPaymentDescription(type),
          payment_method_id: 'pix',
          payer: {
            email: email,
            first_name: user.name.split(' ')[0] || 'Cliente',
            last_name: user.name.split(' ').slice(1).join(' ') || 'AnunciaCerto',
            identification: {
              type: 'CPF',
              number: cleanCpf,
            },
          },
        }),
      });

      const data = await response.json() as any;

      if (!response.ok) {
        console.error('[MERCADO PAGO ERRO API]', data);
        throw new HttpException(
          data.message || 'Falha ao gerar o Pix no Mercado Pago',
          HttpStatus.BAD_GATEWAY,
        );
      }

      const mpId = String(data.id);
      const qrCode = data.point_of_interaction?.transaction_data?.qr_code;
      const qrCodeBase64 = data.point_of_interaction?.transaction_data?.qr_code_base64;

      if (!qrCode || !qrCodeBase64) {
        throw new HttpException(
          'Erro ao obter dados de pagamento Pix do Mercado Pago',
          HttpStatus.BAD_GATEWAY,
        );
      }

      // Cria registro de pagamento no banco local
      const payment = await this.prisma.payment.create({
        data: {
          userId,
          amount,
          mpId,
          status: 'pending',
          type,
        },
      });

      return {
        paymentId: payment.id,
        mpId,
        status: 'pending',
        qrCode,
        qrCodeBase64,
        amount,
      };
    } catch (error) {
      if (error instanceof HttpException) throw error;
      console.error('[ERRO DE REDE MERCADO PAGO]', error);
      throw new HttpException(
        'Erro ao conectar ao gateway de pagamento Mercado Pago',
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  async getPaymentStatus(id: string) {
    const payment = await this.prisma.payment.findUnique({ where: { id } });
    if (!payment) {
      throw new HttpException('Pagamento não encontrado', HttpStatus.NOT_FOUND);
    }

    // Se estiver pendente localmente, consulta na API do Mercado Pago para garantir atualização rápida
    if (payment.status === 'pending') {
      try {
        const url = `https://api.mercadopago.com/v1/payments/${payment.mpId}`;
        const response = await fetch(url, {
          headers: {
            'Authorization': `Bearer ${this.mpAccessToken}`,
          },
        });

        if (response.ok) {
          const data = await response.json() as any;
          const currentStatus = data.status; // "approved", "pending", "rejected", etc.

          const currentLocalStatus: string = payment.status;
          if (currentStatus === 'approved' && currentLocalStatus !== 'approved') {
            await this.updatePaymentToApproved(payment);
            return { id: payment.id, status: 'approved', amount: payment.amount };
          } else if (currentStatus === 'rejected' && currentLocalStatus !== 'rejected') {
            await this.prisma.payment.update({
              where: { id: payment.id },
              data: { status: 'rejected' },
            });
            return { id: payment.id, status: 'rejected', amount: payment.amount };
          }
        }
      } catch (error) {
        console.error('[ERRO CONSULTA PAGAMENTO MP]', error);
      }
    }

    return {
      id: payment.id,
      status: payment.status,
      amount: payment.amount,
    };
  }

  private getPaymentDescription(type: string): string {
    switch (type) {
      case 'plano_prata': return 'Assinatura Anuncia Certo - Plano Prata';
      case 'plano_ouro': return 'Assinatura Anuncia Certo - Plano Ouro';
      case 'rh_premium': return 'Assinatura RH/Empresas - Banco de Talentos';
      case 'formaturas_fisico': return 'Pacote Formaturas - Álbum Físico (Split)';
      case 'formaturas_digital': return 'Pacote Formaturas - Galeria Digital (Split)';
      case 'subscription': return 'Assinatura Robô Spot AI'; // O Robô voltou!
      case 'deposit': return 'Depósito de Saldo Broker'; // O Robô voltou!
      default: return 'Pagamento Plataforma Anuncia Certo';
    }
  }

  async handleWebhook(body: any) {
    console.log('[WEBHOOK MERCADO PAGO]', JSON.stringify(body));

    // Webhook type payment
    const mpId = body?.data?.id || body?.id;
    const action = body?.action || body?.type;

    if (!mpId || (action && action !== 'payment.updated' && action !== 'payment' && body?.type !== 'payment')) {
      return { received: true, ignored: true };
    }

    try {
      // Consulta a API do Mercado Pago para obter o status verificado
      const url = `https://api.mercadopago.com/v1/payments/${mpId}`;
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${this.mpAccessToken}`,
        },
      });

      if (!response.ok) {
        console.error('[ERRO WEBHOOK VERIFICAÇÃO MP] Status:', response.status);
        return { received: true, error: 'verification_failed' };
      }

      const data = await response.json() as any;
      const status = data.status;

      if (status === 'approved') {
        const payment = await this.prisma.payment.findUnique({ where: { mpId: String(mpId) } });
        if (payment && payment.status !== 'approved') {
          await this.updatePaymentToApproved(payment);
          console.log(`[PAGAMENTO APROVADO WEBHOOK] ID MP: ${mpId} | Usuário: ${payment.userId}`);
        }
      } else if (status === 'rejected') {
        const payment = await this.prisma.payment.findUnique({ where: { mpId: String(mpId) } });
        if (payment && payment.status !== 'rejected') {
          await this.prisma.payment.update({
            where: { id: payment.id },
            data: { status: 'rejected' },
          });
        }
      }

      return { received: true, processed: true };
    } catch (error) {
      console.error('[ERRO INTERNO WEBHOOK MP]', error);
      return { received: true, error: 'internal_error' };
    }
  }

  private async updatePaymentToApproved(payment: any) {
    await this.prisma.$transaction(async (tx) => {
      // 1. Atualiza o status do pagamento
      await tx.payment.update({
        where: { id: payment.id },
        data: { status: 'approved' },
      });

      // 2. Concede acesso ou privilégio baseado no tipo de pagamento
      const roleToSet = this.getRoleForPaymentType(payment.type);
      if (roleToSet) {
        await tx.user.update({
          where: { id: payment.userId },
          data: { accountType: roleToSet },
        });
      }

      // 3. Processamento Específico: Split Formaturas
      if (payment.type.startsWith('formaturas_')) {
        await this.processFormaturaSplit(tx, payment);
      }

      // 4. Processamento Específico: Robô Spot AI (RESTAURADO COM SUCESSO!)
      if (payment.type === 'subscription') {
        const existingConfig = await tx.botConfig.findUnique({
          where: { userId: payment.userId },
        });
        if (!existingConfig) {
          await tx.botConfig.create({
            data: {
              userId: payment.userId,
              symbol: 'SOL/USDT',
              tradeAmount: 12.0,
              isActive: false,
            },
          });
        }
      }
    });
  }

  private getRoleForPaymentType(type: string): string | null {
    switch (type) {
      case 'plano_prata': return 'prata';
      case 'plano_ouro': return 'ouro';
      case 'rh_premium': return 'rh_premium';
      default: return null;
    }
  }

  private async processFormaturaSplit(tx: any, payment: any) {
    // =========================================================
    // VARIÁVEIS DE CONFIGURAÇÃO DO SPLIT (FORMATURAS)
    // =========================================================
    
    // 1. Taxa da Plataforma (Altere para 0.20 se quiser 20%, ou 0.25 para 25%)
    const TAXA_PLATAFORMA_PERCENTUAL = 0.25; 

    // 2. Conta/Chave do Fotógrafo (Ainda não definida)
    // No futuro, buscaremos isso no banco (ex: payment.photographerId)
    // onde o fotógrafo cadastrará a conta bancária ou Mercado Pago dele.
    const CHAVE_RECEBEDOR_FOTOGRAFO = "CHAVE_PENDENTE_FOTOGRAFO"; 

    // =========================================================

    const amount = payment.amount;
    const platformFee = amount * TAXA_PLATAFORMA_PERCENTUAL;
    const photographerShare = amount - platformFee;
    
    console.log(`[SPLIT FORMATURAS] Total: R$ ${amount} | Plataforma (${TAXA_PLATAFORMA_PERCENTUAL * 100}%): R$ ${platformFee} | Fotógrafo: R$ ${photographerShare} (Conta Destino: ${CHAVE_RECEBEDOR_FOTOGRAFO})`);
    
    // NOTA PARA O FUTURO (API MERCADO PAGO):
    // Quando o fotógrafo definir o banco dele, a chamada de CreatePixPayment
    // receberá o array de "splits" com a CHAVE_RECEBEDOR_FOTOGRAFO. O Mercado Pago
    // fará a divisão na fonte antes mesmo do dinheiro cair na conta.
  }
}
