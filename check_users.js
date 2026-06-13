const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

async function main() {
  const users = await prisma.user.findMany();
  console.log("=== USERS IN DATABASE ===");
  users.forEach(u => {
    console.log(`ID: ${u.id} | Name: ${u.name} | Email: ${u.email} | Role: ${u.role}`);
  });

  const configs = await prisma.botConfig.findMany();
  console.log("\n=== BOT CONFIGS ===");
  console.log(JSON.stringify(configs, null, 2));
}

main()
  .catch(e => console.error(e))
  .finally(() => prisma.$disconnect());
