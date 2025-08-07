const axios = require('axios');
const fs = require('fs');
const path = require('path');
const { SYSTEM_PROMPT, USER_PROMPT } = require('./prompts');

// Configuration
const FIRECRAWL_URL = 'http://localhost:3002'; // Self-hosted Firecrawl API URL
const API_BASE = `${FIRECRAWL_URL}/v1`;

/**
 * Filters URLs to find About/Team/Leadership pages
 * Prioritizes main team pages and excludes individual team member pages and blog posts
 */
function filterAboutAndTeamPages(urls) {
  // First try to find exact main team pages as highest priority
  const mainTeamPagePatterns = [
    /\/team\/?$/i,                // /team/ pages (main team listing)
    /\/about\/?$/i,               // /about/ pages
    /\/leadership\/?$/i,          // /leadership/ pages
    /\/management\/?$/i,          // /management/ pages
    /\/our-team\/?$/i,            // /our-team/ pages
    /\/about-us\/?$/i,            // /about-us/ pages
    /\/company\/team\/?$/i,       // /company/team/ pages
    /\/company\/about\/?$/i,      // /company/about/ pages
    /\/who-we-are\/?$/i           // /who-we-are/ pages
  ];
  
  // Check if any URLs match the main team page patterns
  const mainTeamPages = urls.filter(url => {
    const path = new URL(url).pathname.toLowerCase();
    return mainTeamPagePatterns.some(pattern => pattern.test(path));
  });
  
  // If we found main team pages, return just those
  if (mainTeamPages.length > 0) {
    return mainTeamPages;
  }
  
  // Otherwise, fall back to keyword search but with better filtering
  const targetKeywords = [
    'about', 'team', 'leadership', 'people',
    'who-we-are', 'our-company', 'founders',
    'executive', 'management', 'board', 'staff', 'directors'
  ];
  
  // Patterns to exclude
  const excludePatterns = [
    /\/blog\//i,                   // Filter out blog posts
    /\/press\//i,                  // Filter out press releases
    /\/podcast\//i,                // Filter out podcast pages
    /\/(team|people)-member\//i,   // Filter out individual team member pages
    /\/author\//i,                 // Filter out author pages
    /\/tag\//i,                    // Filter out tag pages
    /\/category\//i                // Filter out category pages
  ];
  
  return urls.filter(link => {
    const lowerLink = link.toLowerCase();
    
    // Check if URL should be excluded
    if (excludePatterns.some(pattern => pattern.test(lowerLink))) {
      return false;
    }
    
    // Check if URL contains any target keywords
    return targetKeywords.some(keyword => lowerLink.includes(keyword));
  });
}

/**
 * Cleans HTML content
 * - Removes unnecessary elements (navigation, footer, scripts, etc.)
 * - Removes font-related styles and inline styles
 * - Removes excessive whitespace
 * - Normalizes content for better readability
 */
function cleanHtml(html) {
  if (!html) return html;
  
  try {
    // Since we're in Node.js, we'll use regex-based cleaning:
    let cleanedHtml = html;
    
    // Remove HTML comments
    cleanedHtml = cleanedHtml.replace(/<!--[\s\S]*?-->/g, '');
    
    // Remove script tags and their contents
    cleanedHtml = cleanedHtml.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
    
    // Remove style tags and their contents
    cleanedHtml = cleanedHtml.replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, '');
    
    // Remove link tags (stylesheets)
    cleanedHtml = cleanedHtml.replace(/<link[^>]*>/gi, '');
    
    // WOW Image Elements: Remove all <wow-image> tags while keeping the inner <img> tags
    cleanedHtml = cleanedHtml.replace(/<wow-image[^>]*>(.*?<img[^>]*>).*?<\/wow-image>/gi, '$1');
    
    // Remove font tags completely
    cleanedHtml = cleanedHtml.replace(/<font\b[^<]*(?:(?!<\/font>)<[^<]*)*<\/font>/gi, match => {
      // Extract the content between font tags and return just that
      const content = match.replace(/<font[^>]*>|<\/font>/gi, '');
      return content;
    });
    
    // Remove inline styles
    cleanedHtml = cleanedHtml.replace(/(<[^>]*)\s+style=["'][^"']*["']([^>]*>)/gi, '$1$2');
    
    // Remove class attributes (which often contain styling information)
    cleanedHtml = cleanedHtml.replace(/(<[^>]*)\s+class=["'][^"']*["']([^>]*>)/gi, '$1$2');
    
    // Remove width and height attributes
    cleanedHtml = cleanedHtml.replace(/(<[^>]*)\s+width=["']?[^"']*["']?([^>]*>)/gi, '$1$2');
    cleanedHtml = cleanedHtml.replace(/(<[^>]*)\s+height=["']?[^"']*["']?([^>]*>)/gi, '$1$2');
    
    // Remove srcset attributes (alternative image sources)
    cleanedHtml = cleanedHtml.replace(/(<[^>]*)\s+srcset=["'][^"']*["']([^>]*>)/gi, '$1$2');
    
    // Remove fetchpriority attributes
    cleanedHtml = cleanedHtml.replace(/(<[^>]*)\s+fetchpriority=["'][^"']*["']([^>]*>)/gi, '$1$2');
    
    // Remove all data attributes
    cleanedHtml = cleanedHtml.replace(/(<[^>]*)\s+data-[a-z0-9_-]+=["'][^"']*["']([^>]*>)/gi, '$1$2');
    
    // Remove ARIA attributes
    cleanedHtml = cleanedHtml.replace(/(<[^>]*)\s+aria[a-z0-9_-]+=["'][^"']*["']([^>]*>)/gi, '$1$2');
    cleanedHtml = cleanedHtml.replace(/(<[^>]*)\s+role=["'][^"']*["']([^>]*>)/gi, '$1$2');
    cleanedHtml = cleanedHtml.replace(/(<[^>]*)\s+tabindex=["'][^"']*["']([^>]*>)/gi, '$1$2');
    
    // Remove font-family, font-size, color and other style-related attributes
    cleanedHtml = cleanedHtml.replace(/(<[^>]*)\s+font-family=["'][^"']*["']([^>]*>)/gi, '$1$2');
    cleanedHtml = cleanedHtml.replace(/(<[^>]*)\s+font-size=["'][^"']*["']([^>]*>)/gi, '$1$2');
    cleanedHtml = cleanedHtml.replace(/(<[^>]*)\s+color=["'][^"']*["']([^>]*>)/gi, '$1$2');
    cleanedHtml = cleanedHtml.replace(/(<[^>]*)\s+bgcolor=["'][^"']*["']([^>]*>)/gi, '$1$2');
    cleanedHtml = cleanedHtml.replace(/(<[^>]*)\s+face=["'][^"']*["']([^>]*>)/gi, '$1$2');
    
    // Try to remove navigation elements (imperfect but helps)
    cleanedHtml = cleanedHtml.replace(/<nav\b[^<]*(?:(?!<\/nav>)<[^<]*)*<\/nav>/gi, '');
    cleanedHtml = cleanedHtml.replace(/<header\b[^<]*(?:(?!<\/header>)<[^<]*)*<\/header>/gi, '');
    cleanedHtml = cleanedHtml.replace(/<footer\b[^<]*(?:(?!<\/footer>)<[^<]*)*<\/footer>/gi, '');
    
    // Remove common footer/header IDs (Wix, WordPress, etc.)
    cleanedHtml = cleanedHtml.replace(/<div[^>]*id=["']SITE_HEADER["'][^>]*>[\s\S]*?<\/div>/gi, '');
    cleanedHtml = cleanedHtml.replace(/<div[^>]*id=["']SITE_FOOTER["'][^>]*>[\s\S]*?<\/div>/gi, '');
    
    // Remove background elements
    cleanedHtml = cleanedHtml.replace(/<div[^>]*id=["']bgLayers[^"']*["'][^>]*>[\s\S]*?<\/div>/gi, '');
    cleanedHtml = cleanedHtml.replace(/<div[^>]*id=["']BACKGROUND_GROUP["'][^>]*>[\s\S]*?<\/div>/gi, '');
    
    // Remove elements with common background/decoration class names
    cleanedHtml = cleanedHtml.replace(/<div[^>]*class=["'][^"']*(?:background|bg-|bgLayers)[^"']*["'][^>]*>[\s\S]*?<\/div>/gi, '');
    
    // Remove common ad containers
    cleanedHtml = cleanedHtml.replace(/<div[^>]*id=["'][^"']*(?:ad-|banner-|sidebar)[^"']*["'][^>]*>[\s\S]*?<\/div>/gi, '');
    cleanedHtml = cleanedHtml.replace(/<div[^>]*class=["'][^"']*(?:ad-|banner-|sidebar)[^"']*["'][^>]*>[\s\S]*?<\/div>/gi, '');
    
    // Remove social media widgets
    cleanedHtml = cleanedHtml.replace(/<div[^>]*class=["'][^"']*(?:social-|share-)[^"']*["'][^>]*>[\s\S]*?<\/div>/gi, '');
    
    // Remove empty divs and spans
    cleanedHtml = cleanedHtml.replace(/<(div|span)[^>]*>\s*<\/\1>/gi, '');
    
    // Remove hidden elements
    cleanedHtml = cleanedHtml.replace(/<[^>]*style=["'][^"']*(?:display:\s*none|visibility:\s*hidden)[^"']*["'][^>]*>[\s\S]*?<\/[^>]*>/gi, '');
    cleanedHtml = cleanedHtml.replace(/<[^>]*hidden[^>]*>[\s\S]*?<\/[^>]*>/gi, '');
    
    // Remove chat widget
    cleanedHtml = cleanedHtml.replace(/<div[^>]*id=["']pinnedBottomRight["'][^>]*>[\s\S]*?<\/div>/gi, '');
    
    // Remove top and bottom scroll elements
    cleanedHtml = cleanedHtml.replace(/<div[^>]*id=["']SCROLL_TO_TOP["'][^>]*>[\s\S]*?<\/div>/gi, '');
    cleanedHtml = cleanedHtml.replace(/<div[^>]*id=["']SCROLL_TO_BOTTOM["'][^>]*>[\s\S]*?<\/div>/gi, '');
    
    // Remove outer containers that just wrap content
    cleanedHtml = cleanedHtml.replace(/<div[^>]*id=["']SITE_CONTAINER["'][^>]*>([\s\S]*?)<\/div><\/body>/gi, '$1</body>');
    cleanedHtml = cleanedHtml.replace(/<div[^>]*id=["']main_MF["'][^>]*>([\s\S]*?)<\/div><\/div>/gi, '$1</div>');
    
    // Remove excessive whitespace
    cleanedHtml = cleanedHtml.replace(/>\s+</g, '><');
    cleanedHtml = cleanedHtml.replace(/^\s+/gm, '');
    cleanedHtml = cleanedHtml.replace(/\n\s*\n\s*\n/g, '\n\n');
    cleanedHtml = cleanedHtml.replace(/\r\n/g, '\n');
    
    return cleanedHtml;
  } catch (error) {
    console.error('Error cleaning HTML:', error.message);
    return html; // Return original if cleaning fails
  }
}

/**
 * Extract team member data from HTML using OpenAI
 * @param {string} htmlContent - The raw HTML content to analyze
 * @returns {Promise<Array>} - Array of team member objects with name, position, linkedin, and email
 */
async function extractTeamMembers(htmlContent) {
  try {
    console.log('📊 Extracting team members using OpenAI...');
    
    // Use dummy API key for now - will be replaced by the user
    const OPENAI_API_KEY = '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';
    
    if (!OPENAI_API_KEY) {
      console.error("Error: OpenAI API key not found");
      return null;
    }
    
    // The model has a token limit - we need to make sure our HTML isn't too large
    // A rough estimate is that 1 token ~= 4 characters in English
    const MAX_CHARS = 32000; // Keeping a conservative limit
    
    // Prepare the HTML - find and extract the most relevant section if needed
    let processedHtml = htmlContent;
    
    // If the HTML is too large, try to extract just the team section
    if (htmlContent.length > MAX_CHARS) {
      console.log(`⚠️ HTML content is too large (${htmlContent.length} chars). Looking for team section...`);
      
      // Try to find team/people sections using common patterns
      const teamSectionPatterns = [
        /<section[^>]*team[^>]*>[\s\S]*?<\/section>/i,
        /<div[^>]*team[^>]*>[\s\S]*?<\/div>/i,
        /<div[^>]*people[^>]*>[\s\S]*?<\/div>/i,
        /<div[^>]*leadership[^>]*>[\s\S]*?<\/div>/i,
        /<section[^>]*about[^>]*>[\s\S]*?<\/section>/i,
        /<div[^>]*about[^>]*>[\s\S]*?<\/div>/i
      ];
      
      // Try each pattern until we find a match
      let teamSection = null;
      for (const pattern of teamSectionPatterns) {
        const match = htmlContent.match(pattern);
        if (match && match[0]) {
          teamSection = match[0];
          break;
        }
      }
      
      if (teamSection) {
        console.log(`✅ Found a team section (${teamSection.length} chars)`);
        processedHtml = teamSection;
      } else {
        // If we can't find a specific team section, just truncate
        console.log(`⚠️ Couldn't find a specific team section. Truncating HTML...`);
        processedHtml = htmlContent.substring(0, MAX_CHARS);
      }
    }
    
    // Final size check
    if (processedHtml.length > MAX_CHARS) {
      processedHtml = processedHtml.substring(0, MAX_CHARS);
      console.log(`⚠️ Truncated HTML to ${processedHtml.length} chars`);
    }
    
    // Compile the user prompt with HTML content
    const compiledUserPrompt = USER_PROMPT.replace(
      "{htmlData}", 
      processedHtml
    );
    
    // Make the OpenAI API request
    const response = await axios.post(
      'https://api.openai.com/v1/chat/completions',
      {
        model: "gpt-3.5-turbo",
        messages: [
          { role: "system", content: SYSTEM_PROMPT },
          { role: "user", content: compiledUserPrompt }
        ],
        temperature: 0,
        top_p: 1,
        frequency_penalty: 0,
        presence_penalty: 0
      },
      {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${OPENAI_API_KEY}`
        }
      }
    );
    
    const aiResponse = response.data.choices[0].message.content;
    
    // Parse JSON from response
    try {
      // Try to parse the response directly as JSON
      const teamData = JSON.parse(aiResponse);
      console.log(`✅ Successfully extracted ${teamData.length} team members`);
      return teamData;
    } catch (parseError) {
      console.error(`⚠️ JSON parsing error: ${parseError.message}`);
      
      // Try to extract JSON from the response if it contains explanatory text
      try {
        const jsonMatch = aiResponse.match(/\[[\s\S]*\]/);
        if (jsonMatch) {
          const jsonStr = jsonMatch[0];
          const teamData = JSON.parse(jsonStr);
          console.log(`✅ Successfully extracted ${teamData.length} team members after cleanup`);
          return teamData;
        }
      } catch (e) {
        console.error(`⚠️ Failed to extract JSON from response`);
      }
      
      throw new Error(`Failed to parse OpenAI response as JSON`);
    }
  } catch (error) {
    console.error(`❌ Team member extraction failed: ${error.message}`);
    if (error.response) {
      console.error(`Error details: ${error.response.status} - ${JSON.stringify(error.response.data)}`);
      
      if (error.response.status === 400) {
        console.error(`This is likely due to the HTML being too large for the model's token limit.`);
        console.error(`Try using a different HTML extraction approach or truncating the content further.`);
      } else if (error.response.status === 401) {
        console.error(`Authentication error. Make sure to replace the dummy API key with a valid OpenAI API key.`);
        console.error(`You can set it in the .env file or directly in the code.`);
      }
    }
    return [];
  }
}

/**
 * Scrapes HTML content for a given URL
 */
async function scrapePageHtml(url) {
  try {
    console.log(`\n⚡ Scraping content from: ${url}`);
    const response = await axios.post(`${API_BASE}/scrape`, {
      url,
      formats: ['html'] // Only requesting HTML to keep things simple
    }, {
      headers: { 'Content-Type': 'application/json' }
    });

    if (response.data.success) {
      console.log(`✅ Successfully fetched content for ${url}\n`);
      
      // Create outputs directory if it doesn't exist
      const outputDir = 'outputs';
      fs.mkdirSync(outputDir, { recursive: true });
      
      // Create a hostname-based filename without special characters
      const urlObj = new URL(url);
      const hostname = urlObj.hostname.replace(/\./g, '_');
      const pathname = urlObj.pathname.replace(/[^a-zA-Z0-9]/g, '_').replace(/_+/g, '_');
      const baseFileName = `${hostname}${pathname}`.slice(0, 100); // Limit filename length
      
      // Clean HTML before saving
      if (response.data.data.html) {
        const cleanedHtml = cleanHtml(response.data.data.html);
        const htmlFilePath = path.join(outputDir, `${baseFileName}.html`);
        fs.writeFileSync(htmlFilePath, cleanedHtml);
        console.log(`💾 Saved cleaned HTML to ${htmlFilePath}`);
        
        // Save a copy of the original HTML for comparison
        const originalHtmlPath = path.join(outputDir, `${baseFileName}_original.html`);
        fs.writeFileSync(originalHtmlPath, response.data.data.html);
        console.log(`💾 Saved original HTML to ${originalHtmlPath}`);
        
        // Calculate size reduction
        const originalSize = response.data.data.html.length;
        const cleanedSize = cleanedHtml.length;
        const reductionPercent = ((originalSize - cleanedSize) / originalSize * 100).toFixed(2);
        console.log(`🔍 Cleaned HTML is ${reductionPercent}% smaller (${originalSize} → ${cleanedSize} bytes)`);
        
        // Extract team members from the cleaned HTML
        console.log(`\n🧩 Analyzing page for team member information...`);
        const teamMembers = await extractTeamMembers(cleanedHtml);
        
        if (teamMembers && teamMembers.length > 0) {
          // Save team members to JSON file
          const teamDataPath = path.join(outputDir, `${baseFileName}_team.json`);
          fs.writeFileSync(teamDataPath, JSON.stringify(teamMembers, null, 2));
          console.log(`💾 Saved ${teamMembers.length} team members to ${teamDataPath}`);
          
          // Print team members
          console.log(`\n👥 Found team members:`);
          teamMembers.forEach((member, index) => {
            console.log(`${index + 1}. ${member.name} - ${member.position}`);
            if (member.linkedin) console.log(`   LinkedIn: ${member.linkedin}`);
            if (member.email) console.log(`   Email: ${member.email}`);
          });
        } else {
          console.log(`⚠️ No team members found on the page`);
        }
      }
      
      return response.data;
    } else {
      console.error(`❌ Failed to fetch content for ${url}`);
    }
  } catch (error) {
    console.error(`❌ Error scraping page ${url}:`, error.message);
  }
}

/**
 * Maps all URLs from a given webpage using Firecrawl's map functionality
 */
async function mapUrlsFromPage(url, searchTerm = null) {
  try {
    console.log(`Mapping URLs from: ${url}`);
    const payload = { url };
    if (searchTerm) payload.search = searchTerm;

    const response = await axios.post(`${API_BASE}/map`, payload, {
      headers: { 'Content-Type': 'application/json' }
    });

    if (response.data.success || response.data.status === 'success') {
      const allLinks = response.data.links;
      console.log(`\nTotal URLs mapped: ${allLinks.length}`);

      const aboutAndTeamPages = filterAboutAndTeamPages(allLinks);
      console.log(`\n🔍 Found ${aboutAndTeamPages.length} About/Team/Leadership pages:\n`);
      aboutAndTeamPages.forEach((link, idx) => console.log(`${idx + 1}. ${link}`));

      // Scrape HTML from each about/team page
      for (const pageUrl of aboutAndTeamPages) {
        await scrapePageHtml(pageUrl);
      }
    } else {
      console.error('Error: Failed to map URLs');
      console.error(response.data);
    }
  } catch (error) {
    console.error('❌ Error mapping URLs:', error.message);
  }
}

// Example usage
if (require.main === module) {
  const args = ["https://sapphireventures.com/"];

  const url = args[0];
  const searchTerm = args[1] || null;

  mapUrlsFromPage(url, searchTerm);
}

// Export if needed elsewhere
module.exports = { 
  mapUrlsFromPage, 
  filterAboutAndTeamPages, 
  cleanHtml, 
  extractTeamMembers, 
  scrapePageHtml 
};
