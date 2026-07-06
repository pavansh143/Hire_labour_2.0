const mysql = require('mysql2/promise');
const fs = require('fs').promises;
const path = require('path');
require('dotenv').config();

let mode = 'mysql';
let pool;
const MOCK_DB_PATH = path.join(__dirname, 'mock_db.json');

async function initDB() {
    try {
        pool = mysql.createPool({
            host: process.env.DB_HOST,
            user: process.env.DB_USER,
            password: process.env.DB_PASS,
            database: process.env.DB_NAME,
            waitForConnections: true,
            connectionLimit: 10,
            queueLimit: 0
        });
        // Test connection
        await pool.query('SELECT 1');
        console.log('Using MySQL Database');
    } catch (err) {
        console.warn('MySQL Connection failed. Falling back to MOCK JSON Database.');
        mode = 'json';
        if (!require('fs').existsSync(MOCK_DB_PATH)) {
            await fs.writeFile(MOCK_DB_PATH, JSON.stringify({ labourers: [], otp_verifications: [], reviews: [] }));
        }
    }
}

initDB();

module.exports = {
    query: async (sql, params = []) => {
        if (mode === 'mysql') {
            return pool.query(sql, params);
        } else {
            // Very simple JSON-based mock query logic
            const data = JSON.parse(await fs.readFile(MOCK_DB_PATH, 'utf8'));
            
            if (sql.includes('INSERT INTO labourers')) {
                const newLabourer = {
                    id: data.labourers.length + 1,
                    full_name: params[0],
                    phone: params[1],
                    location: params[2],
                    skills: params[3],
                    bio: params[4],
                    aadhaar_number: params[5],
                    id_card_image: params[6],
                    selfie_image: params[7],
                    trust_score: 0,
                    status: 'Pending',
                    created_at: new Date()
                };
                data.labourers.push(newLabourer);
                await fs.writeFile(MOCK_DB_PATH, JSON.stringify(data, null, 2));
                return [{ insertId: newLabourer.id }];
            }
            
            if (sql.includes('SELECT * FROM labourers WHERE id = ?')) {
                const lab = data.labourers.find(l => l.id == params[0]);
                return [lab ? [lab] : []];
            }

            if (sql.includes('UPDATE labourers SET')) {
                const labIndex = data.labourers.findIndex(l => l.id == params[params.length - 1]);
                if (labIndex !== -1) {
                    data.labourers[labIndex].trust_score = params[0];
                    data.labourers[labIndex].status = params[1];
                    data.labourers[labIndex].face_encoding = params[3];
                }
                await fs.writeFile(MOCK_DB_PATH, JSON.stringify(data, null, 2));
                return [{}];
            }

            if (sql.includes('SELECT id, face_encoding')) {
                return [data.labourers.map(l => ({ id: l.id, encoding: l.face_encoding }))];
            }

            if (sql.includes('SELECT * FROM labourers')) {
                return [data.labourers];
            }

            // OTP Mock
            if (sql.includes('INSERT INTO otp_verifications')) {
                data.otp_verifications.push({ phone: params[0], code: params[1] });
                await fs.writeFile(MOCK_DB_PATH, JSON.stringify(data, null, 2));
                return [{}];
            }

            if (sql.includes('SELECT * FROM otp_verifications')) {
                const otp = data.otp_verifications.find(o => o.phone == params[0] && o.code == params[1]);
                return [otp ? [otp] : []];
            }

            return [[]];
        }
    }
};
