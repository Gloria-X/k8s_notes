import { execSync } from 'child_process'
import { randomBytes } from 'crypto'
import fs from 'fs'
import path from 'path'

const ADMIN_ACCESS_KEY = 'xsy-admin'
const ADMIN_SECRET_KEY = 'adminpassw0rd'
const ENDPOINT = 'https://s3.dev.tiusolution.com'
const ALIAS = 'myminio'

const STORAGE_USER = 'user-storage'
const BUCKET_NAME = 'user-storage'
const POLICY_NAME = 'policy_user_storage_bucket'

function runMcCommand(command) {
  return execSync(command, {
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  })
}

/**
 * Provision a MinIO account that can only access the user-storage bucket.
 */
async function provisionUserStorageAccount() {
  const secretKey = `secret_${randomBytes(12).toString('hex')}`
  const policyPath = path.resolve(`${POLICY_NAME}.json`)
  const policy = {
    Version: '2012-10-17',
    Statement: [
      {
        Effect: 'Allow',
        Action: ['s3:GetBucketLocation', 's3:ListBucket'],
        Resource: [`arn:aws:s3:::${BUCKET_NAME}`],
      },
      {
        Effect: 'Allow',
        Action: ['s3:*'],
        Resource: [`arn:aws:s3:::${BUCKET_NAME}/*`],
      },
    ],
  }

  try {
    console.log(`--- Provisioning restricted MinIO account: ${STORAGE_USER} ---`)

    runMcCommand(
      `mc alias set ${ALIAS} ${ENDPOINT} ${ADMIN_ACCESS_KEY} ${ADMIN_SECRET_KEY}`,
    )

    runMcCommand(`mc mb --ignore-existing ${ALIAS}/${BUCKET_NAME}`)
    console.log(`[1/4] Bucket ensured: ${BUCKET_NAME}`)

    fs.writeFileSync(policyPath, JSON.stringify(policy, null, 2))
    runMcCommand(`mc admin policy create ${ALIAS} ${POLICY_NAME} ${policyPath}`)
    console.log(`[2/4] Policy created: ${POLICY_NAME}`)

    runMcCommand(`mc admin user add ${ALIAS} ${STORAGE_USER} ${secretKey}`)
    console.log(`[3/4] User created: ${STORAGE_USER}`)

    runMcCommand(
      `mc admin policy attach ${ALIAS} ${POLICY_NAME} --user ${STORAGE_USER}`,
    )
    console.log(`[4/4] Access restricted to bucket: ${BUCKET_NAME}`)

    return {
      storageId: STORAGE_USER,
      secretKey,
      bucket: BUCKET_NAME,
      mountPoint: '/data',
    }
  } catch (error) {
    const stderr = error.stderr?.toString().trim()
    console.error('Provision failed:', stderr || error.message)
    throw error
  } finally {
    if (fs.existsSync(policyPath)) {
      fs.unlinkSync(policyPath)
    }
  }
}

provisionUserStorageAccount()
  .then((result) => {
    console.log('\n--- Suggested /etc/.passwd-s3fs entry ---')
    console.log(`${result.storageId}:${result.secretKey}`)
    console.log(`bucket=${result.bucket}`)
  })
  .catch(console.error)

// user-storage:secret_5699761b4be947ce125de1f4
// bucket=user-storage
