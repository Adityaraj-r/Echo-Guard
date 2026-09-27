const appUsername = process.env.MONGO_APP_USERNAME;
const appPassword = process.env.MONGO_APP_PASSWORD;
const rootPassword = process.env.MONGO_INITDB_ROOT_PASSWORD;
const appDatabase = process.env.MONGO_INITDB_DATABASE || "echoguard";

if (
  !appUsername ||
  !appPassword ||
  !rootPassword ||
  appPassword.includes("REPLACE_WITH") ||
  rootPassword.includes("REPLACE_WITH")
) {
  throw new Error("MongoDB application user credentials are required.");
}

db.getSiblingDB(appDatabase).createUser({
  user: appUsername,
  pwd: appPassword,
  roles: [{ role: "readWrite", db: appDatabase }],
});
