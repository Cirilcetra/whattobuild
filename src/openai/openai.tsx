import OpenAI from 'openai';

const openai = new OpenAI({
  apiKey: process.env.REACT_APP_OPENAI_API_KEY,
  dangerouslyAllowBrowser: true
});

export interface AnalysisResult {
  mostRequestedIdeas: string[];
  mostFrustratingProblems: string[];
  mostUpvotedSuggestions: string[];
  aiSolvableIdeas: string[];
  recurringProblems: string[];
}

export async function analyzeRedditPosts(posts: any[]): Promise<AnalysisResult> {
  const prompt = `Analyze these Reddit posts and categorize the information into:
1. Most Requested Ideas – Popular product or feature ideas people want
2. Most Frustrating Problems – Issues users frequently complain about
3. Most Upvoted Suggestions – Highly supported recommendations from discussions
4. Ideas That Can Be Solved with AI – Recurring requests that AI could automate or improve
5. Recurring Problems – Common issues that keep resurfacing across threads

Posts data: ${JSON.stringify(posts)}

Please format your response as a JSON object with these keys: mostRequestedIdeas, mostFrustratingProblems, mostUpvotedSuggestions, aiSolvableIdeas, recurringProblems. Each should be an array of strings.`;

  const completion = await openai.chat.completions.create({
    messages: [{ role: "user", content: prompt }],
    model: "gpt-3.5-turbo",
  });

  return JSON.parse(completion.choices[0].message.content || "{}");
}
