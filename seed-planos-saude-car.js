const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

async function main() {
  console.log("Iniciando seed de Planos Saúde Car...");

  const planos = [
    {
      name: 'Saúde Car Básico',
      description: 'Cobertura essencial para o seu veículo. Inclui 2 trocas de óleo por ano, alinhamento e check-up preventivo trimestral.',
      priceMensal: 49.90,
      priceAnual: 499.00,
      features: ['2 Trocas de Óleo/ano', 'Check-up trimestral', 'Alinhamento/Balanceamento (1x/ano)', '10% de desconto em oficinas credenciadas']
    },
    {
      name: 'Saúde Car Total',
      description: 'Tranquilidade completa. Cobertura premium com Guincho 24h, revisões completas e descontos agressivos na rede credenciada.',
      priceMensal: 129.90,
      priceAnual: 1299.00,
      features: ['Troca de Óleo ilimitada (dentro da km)', 'Check-up bimestral', 'Alinhamento/Balanceamento ilimitado', 'Guincho 24h (até 100km)', '30% de desconto em oficinas credenciadas']
    }
  ];

  for (const plano of planos) {
    const p = await prisma.healthPlan.create({
      data: plano
    });
    console.log(` - Plano criado: ${p.name}`);
  }

  console.log("Planos criados com sucesso!");
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });