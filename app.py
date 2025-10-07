import streamlit as st
import requests
import pandas as pd
import time
from io import StringIO

st.set_page_config(page_title="Voice Autocomplete Scraper", page_icon="🎤", layout="wide")

st.title("🎤 Voice Autocomplete Scraper")
st.markdown("Explore Google Suggest with voice-style prompts")

# Instructions section
with st.expander("📖 How to Use & Option Definitions", expanded=False):
    st.markdown("""
    ## How to Use
    
    1. **Enter your seeds** in the sidebar (one per line) - these are your base queries like "hey google" or "ok google"
    2. **Configure locale settings** - set your language code (e.g., "en") and region (e.g., "US", "GB", "CA")
    3. **Choose variant options** - select which exploration methods to use (letters, wildcards, questions)
    4. **Set position options** - decide where to place variants (prefix, infix, suffix)
    5. **Click "Run Scraper"** - the tool will generate variants and fetch suggestions from Google
    6. **Download results** - export your findings as a CSV file
    
    ---
    
    ## Option Definitions
    
    ### Variant Options
    
    **Letters (a-z)** - Adds each letter of the alphabet to your seed to discover suggestions
    - Example: `hey google a`, `hey google b`, `hey google c`, etc.
    
    **Wildcards (*)** - Uses asterisks to discover hidden suggestions
    - Example: `hey google *`, `* hey google`
    - When combined with letters: `hey google*n`, `hey google n*`
    
    **Question words** - Tests common question starters with your seed
    - Includes: how, what, why, when, where, who, which, can, should, will, do, does, is
    - Example: `hey google what`, `hey google how`, `ok google why`
    - When combined with wildcards: `hey google*what`, `hey google what*`
    
    ### Position Options
    
    **Prefix position** - Places variants BEFORE your seed
    - Example: `a hey google`, `what hey google`, `* hey google`
    
    **Infix position** - Places variants BETWEEN words in your seed (only works with multi-word seeds)
    - Example: For seed "hey google": `hey a google`, `hey * google`
    
    **Suffix position** - Places variants AFTER your seed
    - Example: `hey google a`, `hey google what`, `hey google *`
    
    ### Other Settings
    
    **Max queries per variant** - Limits how many variant queries to test per seed (helps control scraping time)
    
    **Language & Region** - Controls which Google locale to query for region-specific suggestions
    - Try combinations like: en-GB + GB, en + CA, es + US for different results
    
    ---
    
    ## Pro Tips
    
    - Start with both Letters and Wildcards enabled in Suffix position for quick, high-value results
    - Try action verbs as seeds: "hey google set", "hey google play", "ok google call"
    - Run multiple passes with different Language/Region combos to find regional variations
    - The tool adds a small delay between requests to be polite to Google's API
    """)
    
st.markdown("---")

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    
    seeds_input = st.text_area(
        "Seeds (one per line)",
        value="hey google\nok google",
        height=100
    )
    
    col1, col2 = st.columns(2)
    with col1:
        lang = st.text_input("Language", value="en")
    with col2:
        gl = st.text_input("Region", value="US")
    
    max_per_variant = st.number_input(
        "Max queries per variant",
        min_value=1,
        max_value=100,
        value=20
    )
    
    st.subheader("Variant Options")
    use_letters = st.checkbox("Letters (a-z)", value=True)
    use_wildcards = st.checkbox("Wildcards (*)", value=True)
    use_questions = st.checkbox("Question words", value=True)
    
    st.subheader("Position Options")
    use_prefix = st.checkbox("Prefix position", value=True)
    use_infix = st.checkbox("Infix position", value=False)
    use_suffix = st.checkbox("Suffix position", value=True)

# Constants
ALPHABET = list('abcdefghijklmnopqrstuvwxyz')
QUESTION_WORDS = ['how', 'what', 'why', 'when', 'where', 'who', 'which', 'can', 'should', 'will', 'do', 'does', 'is']
CONNECTORS = ['']

def fetch_suggestions(query, lang, gl):
    """Fetch suggestions from Google Suggest API"""
    try:
        url = f"https://suggestqueries.google.com/complete/search"
        params = {
            'client': 'firefox',
            'hl': lang,
            'gl': gl,
            'q': query
        }
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        return data[1] if len(data) > 1 else []
    except Exception as e:
        st.warning(f"Error fetching suggestions for '{query}': {str(e)}")
        return []

def generate_variants(seed, use_letters, use_wildcards, use_questions, 
                     use_prefix, use_infix, use_suffix):
    """Generate query variants from a seed"""
    variants = {seed}  # Start with base seed
    
    if use_letters:
        for letter in ALPHABET:
            if use_prefix:
                variants.add(f"{letter} {seed}")
            if use_suffix:
                variants.add(f"{seed} {letter}")
            if use_infix:
                words = seed.split(' ')
                if len(words) > 1:
                    variants.add(f"{words[0]} {letter} {' '.join(words[1:])}")
            
            # Add wildcard+letter combos when both are enabled
            if use_wildcards:
                if use_suffix:
                    variants.add(f"{seed}*{letter}")  # hey google*n
                    variants.add(f"{seed} {letter}*")  # hey google n*
                if use_prefix:
                    variants.add(f"{letter}*{seed}")  # n*hey google
                    variants.add(f"{letter} *{seed}")  # n *hey google
                if use_infix:
                    words = seed.split(' ')
                    if len(words) > 1:
                        variants.add(f"{words[0]}*{letter} {' '.join(words[1:])}")
                        variants.add(f"{words[0]} {letter}*{' '.join(words[1:])}")
    
    if use_wildcards:
        if use_prefix:
            variants.add(f"* {seed}")
        if use_suffix:
            variants.add(f"{seed} *")
        if use_infix:
            words = seed.split(' ')
            if len(words) > 1:
                variants.add(f"{words[0]} * {' '.join(words[1:])}")
    
    if use_questions:
        for qw in QUESTION_WORDS:
            for conn in CONNECTORS:
                if use_prefix:
                    variants.add(f"{qw}{conn}{seed}")
                if use_suffix:
                    variants.add(f"{seed}{conn}{qw}")
            
            # Add wildcard+question combos when both are enabled
            if use_wildcards:
                if use_suffix:
                    variants.add(f"{seed}*{qw}")  # hey google*what
                    variants.add(f"{seed} {qw}*")  # hey google what*
                if use_prefix:
                    variants.add(f"{qw}*{seed}")  # what*hey google
                    variants.add(f"{qw} *{seed}")  # what *hey google
    
    return list(variants)

def run_scraper(seeds_list, lang, gl, max_per_variant, use_letters, use_wildcards,
                use_questions, use_prefix, use_infix, use_suffix):
    """Main scraper logic"""
    all_results = []
    seen = set()
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_seeds = len(seeds_list)
    
    for seed_idx, seed in enumerate(seeds_list):
        variants = generate_variants(
            seed, use_letters, use_wildcards, use_questions,
            use_prefix, use_infix, use_suffix
        )
        
        count = 0
        for variant in variants:
            if count >= max_per_variant:
                break
            
            status_text.text(f"Processing seed {seed_idx + 1}/{total_seeds}: '{seed}' | Variant: '{variant}' ({count + 1}/{max_per_variant})")
            
            suggestions = fetch_suggestions(variant, lang, gl)
            
            for suggestion in suggestions:
                key = f"{seed}|||{suggestion}"
                if key not in seen:
                    seen.add(key)
                    all_results.append({
                        'seed': seed,
                        'variant': variant,
                        'query_sent': variant,
                        'suggestion': suggestion
                    })
            
            count += 1
            progress_bar.progress((seed_idx + count / max_per_variant) / total_seeds)
            
            # Be polite to the API
            time.sleep(0.1)
    
    progress_bar.progress(1.0)
    status_text.text(f"✅ Complete! Found {len(all_results)} unique suggestions.")
    
    return pd.DataFrame(all_results)

# Main action button
if st.button("🔍 Run Scraper", type="primary", use_container_width=True):
    seeds_list = [s.strip() for s in seeds_input.split('\n') if s.strip()]
    
    if not seeds_list:
        st.error("Please enter at least one seed!")
    else:
        with st.spinner("Scraping..."):
            df = run_scraper(
                seeds_list, lang, gl, max_per_variant,
                use_letters, use_wildcards, use_questions,
                use_prefix, use_infix, use_suffix
            )
            
            if not df.empty:
                st.session_state['results_df'] = df
            else:
                st.warning("No results found. Try adjusting your parameters.")

# Display results
if 'results_df' in st.session_state and not st.session_state['results_df'].empty:
    df = st.session_state['results_df']
    
    st.success(f"Found {len(df)} unique suggestions!")
    
    # Download button
    csv = df.to_csv(index=False)
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name="voice_autocomplete_results.csv",
        mime="text/csv",
        use_container_width=True
    )
    
    # Display results table
    st.subheader("Results Preview")
    st.dataframe(
        df[['seed', 'variant', 'suggestion']],
        use_container_width=True,
        height=400
    )
    
    # Statistics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Suggestions", len(df))
    with col2:
        st.metric("Unique Seeds", df['seed'].nunique())
    with col3:
        st.metric("Avg per Seed", f"{len(df) / df['seed'].nunique():.1f}")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; padding: 20px;'>
    Created by Jon Clark, Managing Partner at <a href='https://www.movingtrafficmedia.com/' target='_blank'>Moving Traffic Media</a>. 
    <a href='https://www.linkedin.com/in/ppcmarketing/' target='_blank'>Follow me on LinkedIn</a>.
    </div>
    """,
    unsafe_allow_html=True
)
