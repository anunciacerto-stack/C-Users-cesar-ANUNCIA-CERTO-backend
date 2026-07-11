import { Injectable, NotFoundException, BadRequestException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';

@Injectable()
export class VehiclesService {
  constructor(private prisma: PrismaService) {}

  // Listar todos os veículos
  async listAllVehicles() {
    return this.prisma.vehicleListing.findMany({
      include: {
        healthRecords: {
          orderBy: { serviceDate: 'desc' },
          include: {
            recordedBy: { select: { name: true } },
          },
        },
        owner: { select: { name: true, email: true } },
        healthSubscription: {
          include: {
            plan: true
          }
        }
      },
      orderBy: { createdAt: 'desc' }
    });
  }

  // Criar/Cadastrar novo veículo
  async createVehicle(data: {
    vehicleType: string;
    brand: string;
    model: string;
    year: number;
    plate?: string;
    chassisOrSerial?: string;
    color?: string;
    renavam?: string;
    ownerName?: string;
    ownerDocument?: string;
    ownerPhone?: string;
    ownerEmail?: string;
    ownerCityState?: string;
    images?: string[];
    videoUrl?: string;
    nfcEnabled?: boolean;
    qrEnabled?: boolean;
    isStolen?: boolean;
    isAuction?: boolean;
    isScrap?: boolean;
    judicialBlock?: boolean;
    isPaid?: boolean;
    clicksFisicos?: number;
    clicksVirtuais?: number;
    hideOwnerName?: boolean;
    hidePlate?: boolean;
    forSale?: boolean;
    price?: number;
    ownerId?: string;
  }) {
    // Definir proprietário fallback (guest) se não fornecido
    const ownerId = data.ownerId || 'guest';

    // Gerar publicCode se não fornecido
    const publicCode = data.plate 
      ? `VEI-${data.plate.toUpperCase().replace(/[^A-Z0-9]/g, '')}`
      : `VEI-${Math.floor(1000 + Math.random() * 9000)}`;

    // Verificar se já existe placa duplicada
    if (data.plate) {
      const existing = await this.prisma.vehicleListing.findFirst({
        where: { plate: data.plate }
      });
      if (existing) {
        throw new BadRequestException(`Já existe um veículo cadastrado com a placa ${data.plate}`);
      }
    }

    return this.prisma.vehicleListing.create({
      data: {
        vehicleType: data.vehicleType || 'Carro',
        brand: data.brand || '',
        model: data.model || '',
        year: Number(data.year) || new Date().getFullYear(),
        plate: data.plate || null,
        chassisOrSerial: data.chassisOrSerial || null,
        color: data.color || null,
        renavam: data.renavam || null,
        ownerName: data.ownerName || null,
        ownerDocument: data.ownerDocument || null,
        ownerPhone: data.ownerPhone || null,
        ownerEmail: data.ownerEmail || null,
        ownerCityState: data.ownerCityState || null,
        publicCode,
        images: data.images || [],
        videoUrl: data.videoUrl || null,
        nfcEnabled: !!data.nfcEnabled,
        qrEnabled: !!data.qrEnabled,
        isStolen: !!data.isStolen,
        isAuction: !!data.isAuction,
        isScrap: !!data.isScrap,
        judicialBlock: !!data.judicialBlock,
        isPaid: !!data.isPaid,
        clicksFisicos: Number(data.clicksFisicos) || 0,
        clicksVirtuais: Number(data.clicksVirtuais) || 0,
        hideOwnerName: !!data.hideOwnerName,
        hidePlate: !!data.hidePlate,
        forSale: !!data.forSale,
        price: data.price ? Number(data.price) : null,
        ownerId,
        status: 'active'
      },
    });
  }

  // Increment clicks
  async incrementClicks(id: string, clickType: 'fisico' | 'virtual') {
    const data = clickType === 'fisico' 
      ? { clicksFisicos: { increment: 1 } }
      : { clicksVirtuais: { increment: 1 } };
    return this.prisma.vehicleListing.update({
      where: { id },
      data
    });
  }

  // Consulta por ID ou publicCode de qualquer categoria
  async getVehicleByIdOrPublicCode(idOrCode: string) {
    let lookupCode = idOrCode;
    
    // Tenta encontrar por tagId na tabela NfcTag primeiro
    const tag = await this.prisma.nfcTag.findUnique({
      where: { tagId: idOrCode }
    });
    if (tag && tag.targetId) {
      lookupCode = tag.targetId;
    }

    // 1. Tenta buscar em Veículos
    const vehicle = await this.prisma.vehicleListing.findFirst({
      where: {
        OR: [
          { id: lookupCode },
          { publicCode: lookupCode },
          { plate: lookupCode }
        ]
      },
      include: {
        healthRecords: {
          orderBy: { serviceDate: 'desc' },
          include: {
            recordedBy: { select: { name: true } },
          },
        },
        owner: { select: { name: true, email: true, phone: true } },
        healthSubscription: {
          include: {
            plan: true
          }
        }
      },
    });

    if (vehicle) {
      return {
        ...vehicle,
        category: 'veiculo'
      };
    }

    // 2. Tenta buscar em Animais
    const animal = await this.prisma.animalListing.findFirst({
      where: {
        OR: [
          { id: lookupCode },
          { publicCode: lookupCode }
        ]
      },
      include: {
        owner: { select: { name: true, email: true, phone: true } }
      }
    });

    if (animal) {
      return {
        ...animal,
        category: 'animal'
      };
    }

    // 3. Tenta buscar em Imóveis
    const property = await this.prisma.propertyListing.findFirst({
      where: {
        OR: [
          { id: lookupCode },
          { publicCode: lookupCode }
        ]
      },
      include: {
        owner: { select: { name: true, email: true, phone: true } }
      }
    });

    if (property) {
      return {
        ...property,
        category: 'imovel'
      };
    }

    // 4. Tenta buscar em Perfis de Empresas/Negócios
    const business = await this.prisma.businessProfile.findFirst({
      where: {
        OR: [
          { id: lookupCode },
          { publicCode: lookupCode }
        ]
      },
      include: {
        owner: { select: { name: true, email: true, phone: true } }
      }
    });

    if (business) {
      return {
        ...business,
        category: 'empresa'
      };
    }

    // 5. Tenta buscar em ListingProfile geral
    const listing = await this.prisma.listingProfile.findFirst({
      where: {
        id: lookupCode
      },
      include: {
        user: { select: { name: true, email: true, phone: true } }
      }
    });

    if (listing) {
      return {
        ...listing,
        category: 'geral'
      };
    }

    throw new NotFoundException('Nenhum registro encontrado com o ID ou Código NFC fornecido.');
  }

  // Adicionar registro de manutenção
  async addHealthRecord(vehicleId: string, data: {
    serviceType: string;
    description: string;
    mileage?: number;
    serviceDate?: string | Date;
    documents?: string[];
    recordedById?: string;
    oilType?: string;
    oilChangeMotor?: boolean;
    oilChangeCambioManual?: boolean;
    oilChangeCambioAutomatico?: boolean;
    kmProximaTroca?: number;
    filterAr?: boolean;
    filterOleoMotor?: boolean;
    filterOleoCambio?: boolean;
    warrantyServices?: boolean;
    warrantyParts?: boolean;
    partsReplaced?: string;
    videoUrl?: string;
  }) {
    const vehicle = await this.prisma.vehicleListing.findUnique({
      where: { id: vehicleId }
    });

    if (!vehicle) {
      throw new NotFoundException('Veículo não encontrado.');
    }

    const recordedById = data.recordedById || 'guest';

    return this.prisma.vehicleHealthRecord.create({
      data: {
        vehicleId,
        recordedById,
        serviceType: data.serviceType || 'Troca de Óleo',
        description: data.description || '',
        mileage: data.mileage ? Number(data.mileage) : null,
        serviceDate: data.serviceDate ? new Date(data.serviceDate) : new Date(),
        documents: data.documents || [],
        isVerifiedShop: true,
        oilType: data.oilType || null,
        oilChangeMotor: !!data.oilChangeMotor,
        oilChangeCambioManual: !!data.oilChangeCambioManual,
        oilChangeCambioAutomatico: !!data.oilChangeCambioAutomatico,
        kmProximaTroca: data.kmProximaTroca ? Number(data.kmProximaTroca) : null,
        filterAr: !!data.filterAr,
        filterOleoMotor: !!data.filterOleoMotor,
        filterOleoCambio: !!data.filterOleoCambio,
        warrantyServices: !!data.warrantyServices,
        warrantyParts: !!data.warrantyParts,
        partsReplaced: data.partsReplaced || null,
        videoUrl: data.videoUrl || null
      }
    });
  }

  // Consulta Pública via NFC
  async getVehicleByPublicCode(publicCode: string) {
    const vehicle = await this.prisma.vehicleListing.findUnique({
      where: { publicCode },
      include: {
        healthRecords: {
          orderBy: { serviceDate: 'desc' },
          include: {
            recordedBy: { select: { name: true } },
          },
        },
        owner: { select: { name: true } },
        healthSubscription: {
          include: {
            plan: true
          }
        }
      },
    });

    if (!vehicle) {
      throw new NotFoundException('Veículo não encontrado ou não cadastrado na plataforma.');
    }

    // Regras de Privacidade Jurídica
    if (vehicle.hideOwnerName && vehicle.owner) {
      vehicle.owner.name = 'Proprietário Confidencial';
    }
    
    if (vehicle.hidePlate && vehicle.plate) {
      // Mascara a placa (Ex: ABC-1234 vira ABC-****)
      if (vehicle.plate.length >= 7) {
        vehicle.plate = vehicle.plate.substring(0, 3) + '-****';
      }
    }

    return vehicle;
  }

  // --- Rede Saúde Car ---
  
  async getHealthPlans() {
    return this.prisma.healthPlan.findMany({
      where: { isActive: true },
      orderBy: { priceMensal: 'asc' }
    });
  }

  async subscribeVehicleToPlan(vehicleId: string, userId: string, planId: string, paymentType: string) {
    const plan = await this.prisma.healthPlan.findUnique({ where: { id: planId } });
    if (!plan) throw new NotFoundException('Plano não encontrado.');

    return this.prisma.vehicleHealthSubscription.upsert({
      where: { vehicleId },
      update: {
        planId,
        paymentType,
        status: 'active',
        userId
      },
      create: {
        vehicleId,
        userId,
        planId,
        paymentType,
        status: 'active'
      }
    });
  }
}
