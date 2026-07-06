const axios = require('axios');

async function analyzeText(text, type) {
    if (!process.env.OPENAI_API_KEY || process.env.OPENAI_API_KEY === 'your_openai_api_key_here') {
        console.warn('OpenAI API Key not set. Skipping analysis.');
        return { is_suspicious: false, score: 0 };
    }

    const prompt = type === 'bio' 
        ? `Analyze this labourer profile bio for spam, copied content, or suspicious patterns. Return JSON with 'is_suspicious' (boolean) and 'reason' (string): "${text}"`
        : `Analyze this review for fake or repeated patterns. Return JSON with 'is_suspicious' (boolean) and 'reason' (string): "${text}"`;

    try {
        const response = await axios.post('https://api.openai.com/v1/chat/completions', {
            model: "gpt-3.5-turbo",
            messages: [{ role: "user", content: prompt }],
            response_format: { type: "json_object" }
        }, {
            headers: {
                'Authorization': `Bearer ${process.env.OPENAI_API_KEY}`,
                'Content-Type': 'application/json'
            }
        });

        return JSON.parse(response.data.choices[0].message.content);
    } catch (err) {
        console.error('OpenAI Error:', err.message);
        return { is_suspicious: false, score: 0 };
    }
}

module.exports = { analyzeText };
