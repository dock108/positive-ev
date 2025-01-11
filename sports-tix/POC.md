# Predicting Ticket Prices During Baseball Season with Machine Learning

## Objective
The goal is to build a machine learning model that predicts ticket prices for baseball games during the season, enabling potential opportunities to profit from price fluctuations.

## Scope
- Focus on ticket prices for a specific baseball team or subset of teams as the initial target.
- Analyze pricing trends on platforms like StubHub, SeatGeek, and others.
- Evaluate market behavior near game days, accounting for factors like demand, team performance, and weather.
- Ensure profitability accounts for high buy and sell fees, targeting at least a 15-20% profit margin.

---

## Phases

### **Phase 1: Data Collection**
1. **Identify Data Sources**
   - Use APIs or web scraping for StubHub, SeatGeek, etc.
   - Supplement with historical ticket price data if available.

2. **Data Points to Collect**
   - Ticket prices (listing and sale prices)
   - Game date and time
   - Teams playing
   - Stadium location and seating section
   - External factors: weather, team performance, injuries, etc.

3. **Set Up Infrastructure**
   - Use Python with libraries like `Selenium`, `BeautifulSoup`, or `requests` for web scraping.
   - Store data in a database (e.g., PostgreSQL or SQLite) or a CSV/Parquet file for analysis.

---

### **Phase 2: Exploratory Data Analysis (EDA)**
1. Analyze historical ticket prices:
   - Price trends as game day approaches.
   - Impact of team performance, rivalry games, and weather conditions.
   - Identify opportunities where price fluctuations could offer a 15-20% profit margin after fees.
2. Visualize data to identify patterns:
   - Use tools like `matplotlib` and `seaborn`.
3. Identify key features for modeling.

---

### **Phase 3: Model Development**
1. **Feature Engineering**
   - Create features based on date (day of the week, holidays).
   - Include dynamic features like team win streaks, player injuries, and opponent strength.
   - Use categorical encoding for teams and stadiums.

2. **Model Selection**
   - Start with simple regression models (e.g., linear regression).
   - Test advanced models like Random Forests, Gradient Boosting (XGBoost, LightGBM), or Neural Networks.

3. **Training and Validation**
   - Split data into training, validation, and test sets.
   - Use cross-validation to ensure robust performance.

4. **Performance Metrics**
   - Evaluate using RMSE, MAE, and R².
   - Prioritize interpretability for actionable insights.
   - Include analysis on how predicted profits align with the 15-20% target margin after fees.

---

### **Phase 4: Deployment**
1. **Create a Prediction Interface**
   - Build a Flask or FastAPI application for predictions.
   - Input: game details, current ticket prices, and market factors.
   - Output: predicted ticket price range and potential profit margin.

2. **Automated Alerts**
   - Set up notifications for significant pricing discrepancies that meet profit margin criteria.

3. **Scalability**
   - Deploy on cloud platforms like AWS, GCP, or Azure.
   - Use Docker for containerization and CI/CD pipelines for updates.

---

### **Phase 5: Testing and Iteration**
1. Backtest the model using historical data to measure profitability.
2. Focus on filtering results for opportunities that offer 15-20% profit after fees.
3. Fine-tune the model based on real-world performance.
4. Incorporate feedback loops for continuous learning.

---

## Potential Challenges
1. **High Buy and Sell Fees**: Difficulty finding opportunities with a 15-20% profit margin to counteract current fees.
2. Limited availability of historical ticket pricing data.
3. Dynamic market changes (e.g., unexpected demand spikes).
4. API rate limits or legal restrictions on data usage.

---

## Tools and Technologies
- **Programming Languages**: Python (primary), SQL
- **Libraries/Frameworks**: `pandas`, `scikit-learn`, `TensorFlow`, `matplotlib`, `Flask`
- **Databases**: PostgreSQL or SQLite
- **Deployment**: Docker, AWS/GCP/Azure

---

## Success Criteria
1. Model predicts ticket prices with a high degree of accuracy.
2. Identifies profitable buying or selling opportunities.
3. Generates consistent profits when applied in real-world scenarios.
4. Ensures all opportunities meet or exceed a 15-20% profit margin to counteract fees.

---

## Timeline
| Phase                | Duration      | Target Completion |
|----------------------|---------------|--------------------|
| Phase 1: Data Collection    | 2 weeks       | TBD                |
| Phase 2: EDA                | 1 week        | TBD                |
| Phase 3: Model Development  | 3 weeks       | TBD                |
| Phase 4: Deployment         | 2 weeks       | TBD                |
| Phase 5: Testing and Iteration | Ongoing    | TBD                |

---

## Next Steps
1. Finalize the list of data sources.
2. Set up a development environment and basic infrastructure.
3. Begin data collection and exploration.
