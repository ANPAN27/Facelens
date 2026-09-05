const hre = require("hardhat");

async function main() {
  const FaceVerification = await hre.ethers.getContractFactory("FaceVerification");
  const contract = await FaceVerification.deploy();
  await contract.waitForDeployment();

  const address = await contract.getAddress();
  console.log("FaceVerification deployed to:", address);
  console.log("Update CONTRACT_ADDRESS in .env with this address");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
