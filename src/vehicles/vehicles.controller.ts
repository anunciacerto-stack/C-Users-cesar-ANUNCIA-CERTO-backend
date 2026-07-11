import { Controller, Get, Param, Post, Body } from '@nestjs/common';
import { VehiclesService } from './vehicles.service';

@Controller('vehicles')
export class VehiclesController {
  constructor(private readonly vehiclesService: VehiclesService) {}

  // Listar todos os veículos cadastrados
  @Get()
  async getAllVehicles() {
    return this.vehiclesService.listAllVehicles();
  }

  // Cadastrar novo veículo
  @Post()
  async createVehicle(@Body() body: any) {
    return this.vehiclesService.createVehicle(body);
  }

  // Obter veículo específico por ID, Placa ou publicCode
  @Get(':id')
  async getVehicleById(@Param('id') id: string) {
    return this.vehiclesService.getVehicleByIdOrPublicCode(id);
  }

  // Incrementar cliques (físicos ou virtuais)
  @Post(':id/click')
  async incrementClick(@Param('id') id: string, @Body() body: { type: 'fisico' | 'virtual' }) {
    return this.vehiclesService.incrementClicks(id, body.type);
  }

  // Adicionar registro de manutenção
  @Post(':id/records')
  async addRecord(@Param('id') id: string, @Body() body: any) {
    return this.vehiclesService.addHealthRecord(id, body);
  }

  // Rota chamada quando o celular encosta no adesivo NFC
  @Get('nfc/:code')
  async getVehicleByNfc(@Param('code') code: string) {
    return this.vehiclesService.getVehicleByPublicCode(code);
  }

  // Listar planos Saúde Car disponíveis
  @Get('health-plans')
  async getHealthPlans() {
    return this.vehiclesService.getHealthPlans();
  }

  // Assinar um plano (Rede Saúde Car)
  @Post('subscribe')
  async subscribe(@Body() body: { vehicleId: string, userId: string, planId: string, paymentType: string }) {
    return this.vehiclesService.subscribeVehicleToPlan(
      body.vehicleId, 
      body.userId, 
      body.planId, 
      body.paymentType
    );
  }
}
