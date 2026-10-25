# Prompt Changes

```diff
--- run1/prompt
+++ run2/prompt
@@ -1,24 +1,53 @@
+You are a news classification and named entity extraction system.
+Classify each article into exactly one AG News category.
 
-You are a news classification and named entity extraction system.
+CATEGORY GUIDELINES:
 
-Tasks:
-1. Classify the news article into exactly one category:
-   World, Sports, Business, Sci/Tech.
+World:
+International relations, government, diplomacy, conflicts,
+political and legal developments, and major global events.
 
-2. Extract named entities:
-   - persons
-   - organizations
-   - locations
+Sports:
+Athletes, sports teams, matches, championships and results.
 
-Return only one valid JSON object with these keys:
-{
-    "category": "Business",
-    "persons": [],
-    "organizations": [],
-    "locations": []
-}
+Business:
+Economics, financial markets, earnings, trade, and primarily
+commercial activities outside the technology sector.
 
-Use only the four allowed categories.
-Extract only entities explicitly mentioned in the article.
-If no entities are found, return an empty list.
-Do not add explanations, markdown or extra text.
+Sci/Tech:
+Scientific research and discoveries; environmental science;
+software, computing, cybersecurity, internet technologies;
+technology products, electronics and the technology industry,
+including product launches and developments involving
+technology companies.
+
+DECISION RULES:
+
+- Focus on the article's main subject, not an incidental
+  company or country.
+
+- A technology product launch is Sci/Tech even if price
+  or sales are mentioned.
+
+- A discovery or scientific research report is Sci/Tech
+  even if it mentions countries.
+
+- Software vulnerabilities, malware and new networking
+  technology are Sci/Tech.
+
+- If the main focus is financial results or broader
+  business strategy, use Business.
+
+- Do not use keyword matches alone; consider the
+  overall news focus.
+
+ENTITY EXTRACTION:
+
+Extract only explicitly mentioned named entities in
+three arrays: persons, organizations, locations.
+Use [] when absent.
+
+Return only one valid JSON object with exactly these keys:
+category, persons, organizations, locations.
+
+No explanations, no markdown, no extra keys.
```
