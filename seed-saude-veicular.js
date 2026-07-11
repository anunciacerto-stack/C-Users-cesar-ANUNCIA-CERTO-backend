const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

async function main() {
  console.log("Iniciando seed de categorias: Saúde Veicular...");

  // 1. Criar a categoria principal
  let catPrincipal = await prisma.category.findFirst({
    where: { nome: 'Saúde Veicular', parentId: null },
  });

  if (!catPrincipal) {
    catPrincipal = await prisma.category.create({
      data: { nome: 'Saúde Veicular' }
    });
  }

  console.log("Categoria Principal criada/encontrada:", catPrincipal.nome);

  // 2. Criar as subcategorias
  const subcategorias = [
    'Consultas Veiculares (Laudos)',
    'Rede Saúde Car (Assinaturas)',
    'Mecânica Geral',
    'Auto Elétrica',
    'Borracharia e Pneus',
    'Troca de Óleo e Fluidos',
    'Guincho e Socorro 24h',
    'Estética Automotiva'
  ];

  for (const sub of subcategorias) {
    let subCat = await prisma.category.findFirst({
      where: { nome: sub, parentId: catPrincipal.id }
    });
    
    if (!subCat) {
      await prisma.category.create({
        data: { nome: sub, parentId: catPrincipal.id }
      });
      console.log(` - Subcategoria criada: ${sub}`);
    } else {
      console.log(` - Subcategoria já existe: ${sub}`);
    }
  }

  console.log("Seed finalizado com sucesso!");
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
