import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.REACT_APP_SUPABASE_URL!;
const supabaseKey = process.env.REACT_APP_SUPABASE_ANON_KEY!;

export const supabase = createClient(supabaseUrl, supabaseKey);

export interface RedditPost {
  id: string;
  title: string;
  content: string;
  score: number;
  num_comments: number;
  created_utc: number;
  subreddit: string;
  url: string;
  embedding: number[] | null;
} 