import streamlit as st
# Set page config at the very beginning
st.set_page_config(page_title="AgentK8s", layout="wide")

import boto3
import json
import plotly.express as px
import plotly.graph_objects as go
from fpdf import FPDF
from datetime import datetime
import os
from dotenv import load_dotenv
import logging
import sys

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Add logging for debugging
logging.basicConfig(level=logging.INFO)

# Load environment variables from .env file if present
load_dotenv()

# Define default values
DEFAULT_VALUES = {
    "💡 Cluster Health": {
        "Cluster Status": """EKS cluster is running in us-west-2 with 3 availability zones. Current control plane health is good with no reported issues. API server response time averages 200ms. etcd cluster is healthy with no leader elections in past 30 days.""",
        
        "Node Health": """Running 15 nodes across 3 node groups:
- 8 x m5.2xlarge (Production workloads)
- 4 x c5.xlarge (Batch processing)
- 3 x t3.large (Development workloads)
2 nodes reported kubelet connectivity issues last week. Memory pressure observed on 3 production nodes during peak hours.""",
        
        "Pod Scheduling Issues": """- 15% pods experiencing scheduling delays due to resource constraints
- 5 pods stuck in Pending state due to PersistentVolume binding issues
- Occasional pod evictions observed due to node memory pressure
- Resource quotas hitting limits during deployment peaks"""
    },
    "💸 Cost Optimization": {
        "Resource Utilization": """- Average CPU utilization: 45%
- Average Memory utilization: 78%
- 30% of PersistentVolumes underutilized
- Identified 5 idle EBS volumes
- Spot instances not currently utilized""",
        
        "Cost Allocation": """- Monthly EKS costs: $2,500
- EC2 instances: $8,000/month
- EBS volumes: $800/month
- No cost allocation tags implemented
- Missing chargeback mechanism for teams""",
        
        "Optimization Opportunities": """- Right-sizing potential for 6 nodes
- Spot instance adoption possible for non-critical workloads
- Implement automatic scaling for dev environments
- Storage class optimization needed
- Consider Graviton instances for cost reduction"""
    },
    "🔐 Security": {
        "IAM Configuration": """- IRSA (IAM Roles for Service Accounts) partially implemented
- 5 shared IAM roles identified
- Pod security policies not enforced
- Root account access detected in audit logs
- AWS Security Hub integration missing""",
        
        "Secret Management": """- Using AWS Secrets Manager for 60% of secrets
- Some secrets still in plain ConfigMaps
- External Secrets Operator not implemented
- No secret rotation policy
- Key management using AWS KMS""",
        
        "Network Policies": """- Default deny policies missing
- No microsegmentation implemented
- Calico network policies partially configured
- Public endpoints exposed without WAF
- Security groups need tightening"""
    },
    "📈 Monitoring": {
        "Monitoring Tools": """- Prometheus/Grafana stack deployed
- AWS CloudWatch Container Insights enabled
- X-Ray tracing implemented for 40% of services
- Custom metrics pipeline using Prometheus Operator
- Logging via EFK stack""",
        
        "Alert Configuration": """- Node-level alerts configured
- Pod-level resource alerts active
- Missing alerts for PV capacity
- SLO/SLI monitoring needed
- No alert correlation system""",
        
        "Metric Collection": """- Custom metrics for business KPIs
- Standard kubernetes metrics collected
- Missing some network flow metrics
- Retention period: 15 days
- Storage optimization needed"""
    },
    "⚙️ CI/CD": {
        "Pipeline Setup": """- GitLab CI/CD with ArgoCD
- Image scanning with Trivy
- Automated testing coverage: 75%
- Manual approval gates for production
- Jenkins legacy pipelines still active""",
        
        "Deployment Strategy": """- Mix of rolling updates and blue/green
- No canary deployments implemented
- Average deployment frequency: 8/day
- MTTR (Mean Time to Recovery): 45 mins
- Change failure rate: 12%""",
        
        "Rollback Process": """- Manual rollback procedures
- No automated rollback triggers
- Average rollback time: 15 minutes
- Version control for all deployments
- Missing automatic health checks"""
    },
    "🧩 Others": {
        "EKS Version": """- Currently on EKS 1.24
- Planning upgrade to 1.27
- Add-ons require updates
- Custom admission controllers need compatibility testing
- CNI version: 1.12.0""",
        
        "Cluster Architecture": """- Multi-AZ deployment
- Private networking with VPC endpoints
- Transit Gateway integration
- Direct Connect hybrid connectivity
- Running on EC2 with managed node groups""",
        
        "Special Requirements": """- PCI compliance requirements
- 99.99% uptime SLA
- DR RPO: 15 minutes
- DR RTO: 4 hours
- GPU nodes needed for ML workloads"""
    }
}
class AgentK8s:
    def __init__(self):
        self.bedrock = None
        self.ares_tool = None
        self.initialized = False

    def initialize_bedrock(self, aws_access_key, aws_secret_key, region):
        try:
            self.bedrock = boto3.client(
                service_name='bedrock-runtime',
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=region
            )
            return True
        except Exception as e:
            st.error(f"Failed to initialize Bedrock: {str(e)}")
            return False

    def initialize_ares(self, ares_api_key, openai_api_key):
        try:
            os.environ['TRAVERSAAL_ARES_API_KEY'] = ares_api_key
            os.environ['OPENAI_API_KEY'] = openai_api_key
            
            from agentpro.tools.ares_tool import AresInternetTool
            self.ares_tool = AresInternetTool()
            return True
        except Exception as e:
            st.error(f"Failed to initialize Ares: {str(e)}")
            logging.error(f"Initialization error: {str(e)}", exc_info=True)
            return False

    def search_documentation(self, query):
        try:
            if not self.ares_tool:
                raise ValueError("Ares tool not initialized")
            results = self.ares_tool.run(query)
            
            processed_results = []
            if isinstance(results, list):
                for result in results:
                    if isinstance(result, str):
                        processed_results.append({
                            'title': result,
                            'url': '#'
                        })
                    elif isinstance(result, dict):
                        processed_results.append(result)
            
            return processed_results
        except Exception as e:
            st.error(f"Documentation search failed: {str(e)}")
            return []

    def generate_risk_metrics(self):
        risks = {
            'Critical': 2,
            'High': 3,
            'Medium': 4,
            'Low': 5
        }
        
        fig = go.Figure(data=[
            go.Bar(
                x=list(risks.keys()),
                y=list(risks.values()),
                marker_color=['red', 'orange', 'yellow', 'green']
            )
        ])
        fig.update_layout(
            title="Risk Distribution",
            xaxis_title="Risk Level",
            yaxis_title="Number of Findings"
        )
        return fig

    def generate_report(self, inputs):
        try:
            # Create PDF with larger page format for better layout
            class PDF(FPDF):
                def __init__(self):
                    super().__init__('P', 'mm', 'Letter')
                
                def footer(self):
                    self.set_y(-15)
                    self.set_font('Arial', 'I', 8)
                    self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')

            pdf = PDF()
            pdf.alias_nb_pages()
            pdf.add_page()
            
            # Add title with better formatting
            pdf.set_font('Arial', 'B', 24)
            pdf.set_fill_color(240, 240, 240)
            pdf.cell(0, 20, 'EKS Operational Review Report', 0, 1, 'C', True)
            pdf.ln(10)

            # Add current date
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 10, f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 0, 1)
            pdf.ln(5)

            # Executive Summary with better formatting
            pdf.set_font('Arial', 'B', 16)
            pdf.set_fill_color(230, 230, 230)
            pdf.cell(0, 10, 'Executive Summary', 0, 1, 'L', True)
            pdf.set_font('Arial', '', 12)
            pdf.multi_cell(0, 10, 'This report provides a comprehensive review of the EKS cluster operations and identifies key areas for improvement. The assessment covers cluster health, cost optimization, security, monitoring, CI/CD, and other critical aspects of the EKS infrastructure.')
            pdf.ln(5)

            # Add Risk Distribution Chart
            pdf.add_page()
            pdf.set_font('Arial', 'B', 16)
            pdf.set_fill_color(230, 230, 230)
            pdf.cell(0, 10, 'Risk Assessment Overview', 0, 1, 'L', True)
            
            # Generate risk chart using plotly
            risks = {
                'Critical': 2,
                'High': 3,
                'Medium': 4,
                'Low': 5
            }
            
            fig = go.Figure(data=[
                go.Bar(
                    x=list(risks.keys()),
                    y=list(risks.values()),
                    marker_color=['red', 'orange', 'yellow', 'green']
                )
            ])
            fig.update_layout(
                title="Risk Distribution",
                width=700,
                height=400
            )
            
            # Save the chart as an image
            chart_path = "risk_chart.png"
            fig.write_image(chart_path)
            
            # Add the chart to PDF
            pdf.image(chart_path, x=10, y=None, w=190)
            os.remove(chart_path)  # Clean up the temporary file
            pdf.ln(10)

            # Add content for each pillar with better formatting
            pillar_titles = {
                "💡 Cluster Health": "Cluster Health",
                "💸 Cost Optimization": "Cost Optimization",
                "🔐 Security": "Security",
                "📈 Monitoring": "Monitoring",
                "⚙️ CI/CD": "CI/CD",
                "🧩 Others": "Others"
            }

            for pillar, data in inputs.items():
                pdf.add_page()
                pdf.set_font('Arial', 'B', 16)
                pdf.set_fill_color(230, 230, 230)
                clean_title = pillar_titles.get(pillar, pillar)
                pdf.cell(0, 10, clean_title, 0, 1, 'L', True)
                
                for field, content in data.items():
                    if content.strip():
                        pdf.set_font('Arial', 'B', 14)
                        pdf.cell(0, 10, field + ":", 0, 1)
                        pdf.set_font('Arial', '', 12)
                        pdf.multi_cell(0, 10, content)
                    pdf.ln(5)

            # Add Best Practices and References
            pdf.add_page()
            pdf.set_font('Arial', 'B', 16)
            pdf.set_fill_color(230, 230, 230)
            pdf.cell(0, 10, 'Best Practices & References', 0, 1, 'L', True)
            
            best_practices = [
                {
                    'category': 'Security',
                    'link': 'https://docs.aws.amazon.com/eks/latest/userguide/security.html',
                    'description': 'AWS EKS Security Best Practices'
                },
                {
                    'category': 'Cost Optimization',
                    'link': 'https://aws.amazon.com/blogs/containers/cost-optimization-for-kubernetes-on-aws/',
                    'description': 'Cost Optimization for Kubernetes on AWS'
                },
                {
                    'category': 'Operations',
                    'link': 'https://aws.github.io/aws-eks-best-practices/',
                    'description': 'EKS Best Practices Guide'
                },
                {
                    'category': 'Networking',
                    'link': 'https://docs.aws.amazon.com/eks/latest/userguide/network_reqs.html',
                    'description': 'EKS Networking Best Practices'
                }
            ]

            for practice in best_practices:
                pdf.set_font('Arial', 'B', 12)
                pdf.cell(0, 10, practice['category'], 0, 1)
                pdf.set_font('Arial', '', 12)
                pdf.set_text_color(0, 0, 255)
                pdf.cell(0, 10, practice['link'], 0, 1)
                pdf.set_text_color(0, 0, 0)
                pdf.multi_cell(0, 10, practice['description'])
                pdf.ln(5)

            # Add recommendations with priority indicators
            pdf.add_page()
            pdf.set_font('Arial', 'B', 16)
            pdf.set_fill_color(230, 230, 230)
            pdf.cell(0, 10, 'Recommendations', 0, 1, 'L', True)

            timeframes = {
                'Short Term (3 months)': [
                    {'rec': 'Implement automated node health checks', 'priority': 'High'},
                    {'rec': 'Configure cluster autoscaling', 'priority': 'High'},
                    {'rec': 'Enable container vulnerability scanning', 'priority': 'Critical'}
                ],
                'Medium Term (6 months)': [
                    {'rec': 'Implement GitOps practices', 'priority': 'Medium'},
                    {'rec': 'Set up cross-region disaster recovery', 'priority': 'High'},
                    {'rec': 'Implement cost allocation tags', 'priority': 'Medium'}
                ],
                'Long Term (>6 months)': [
                    {'rec': 'Migrate to newer EKS version', 'priority': 'Medium'},
                    {'rec': 'Implement service mesh', 'priority': 'Low'},
                    {'rec': 'Set up multi-cluster management', 'priority': 'Medium'}
                ]
            }

            priority_colors = {
                'Critical': (255, 0, 0),
                'High': (255, 165, 0),
                'Medium': (255, 255, 0),
                'Low': (0, 255, 0)
            }

            for timeframe, recommendations in timeframes.items():
                pdf.set_font('Arial', 'B', 14)
                pdf.cell(0, 10, timeframe, 0, 1)
                pdf.set_font('Arial', '', 12)
                for rec in recommendations:
                    color = priority_colors.get(rec['priority'], (0, 0, 0))
                    pdf.set_text_color(*color)
                    pdf.multi_cell(0, 10, f"[{rec['priority']}] - {rec['rec']}")
                pdf.set_text_color(0, 0, 0)
                pdf.ln(5)

            # Save the PDF
            pdf_output = "eks_review_report.pdf"
            pdf.output(pdf_output)
            return pdf_output

        except Exception as e:
            st.error(f"Failed to generate report: {str(e)}")
            logging.error(f"Report generation error: {str(e)}", exc_info=True)
            return None


def main():
    st.title("AgentK8s - EKS Operational Review Agent 🤖")

    # Initialize session state
    if 'agent' not in st.session_state:
        st.session_state.agent = AgentK8s()
        st.session_state.initialized = False

    # Sidebar for credentials
    with st.sidebar:
        st.header("Credentials")
        with st.form("credentials_form"):
            aws_access_key = st.text_input("AWS Access Key", type="password")
            aws_secret_key = st.text_input("AWS Secret Key", type="password")
            aws_region = st.text_input("AWS Region", value="us-east-1")
            ares_api_key = st.text_input("Traversaal Ares API Key", type="password")
            openai_api_key = st.text_input("OpenAI API Key", type="password")
            
            submit_button = st.form_submit_button("Initialize")
            
            if submit_button:
                if aws_access_key and aws_secret_key and ares_api_key and openai_api_key:
                    if (st.session_state.agent.initialize_bedrock(aws_access_key, aws_secret_key, aws_region) and 
                        st.session_state.agent.initialize_ares(ares_api_key, openai_api_key)):
                        st.session_state.initialized = True
                        st.success("Successfully initialized!")
                else:
                    st.error("Please provide all required credentials")

    # Main content
    if not st.session_state.initialized:
        st.warning("Please initialize the agent with your credentials first")
        return

    pillars = {
        "💡 Cluster Health": {
            "description": "Cluster Status, Node Status, Scheduling issues, etc.",
            "fields": ["Cluster Status", "Node Health", "Pod Scheduling Issues"]
        },
        "💸 Cost Optimization": {
            "description": "Cost concerns, unused resources, right-sizing opportunities.",
            "fields": ["Resource Utilization", "Cost Allocation", "Optimization Opportunities"]
        },
        "🔐 Security": {
            "description": "IAM roles, secrets management, network policies, etc.",
            "fields": ["IAM Configuration", "Secret Management", "Network Policies"]
        },
        "📈 Monitoring": {
            "description": "Tooling, dashboards, alerts, metrics setup.",
            "fields": ["Monitoring Tools", "Alert Configuration", "Metric Collection"]
        },
        "⚙️ CI/CD": {
            "description": "Deployment frequency, pipeline tools, rollback strategy.",
            "fields": ["Pipeline Setup", "Deployment Strategy", "Rollback Process"]
        },
        "🧩 Others": {
            "description": "Kubernetes version, architecture, special needs.",
            "fields": ["EKS Version", "Cluster Architecture", "Special Requirements"]
        }
    }

    inputs = {}
    for pillar, data in pillars.items():
        st.header(pillar)
        st.text(data["description"])
        
        pillar_inputs = {}
        for field in data["fields"]:
            default_value = DEFAULT_VALUES.get(pillar, {}).get(field, "")
            pillar_inputs[field] = st.text_area(
                f"{field}", 
                value=default_value,
                height=200 if len(default_value.split('\n')) > 5 else 100,
                key=f"{pillar}_{field}"
            )
        inputs[pillar] = pillar_inputs

    # Add a clear button to reset to defaults
    if st.button("Reset to Defaults"):
        for pillar, data in pillars.items():
            for field in data["fields"]:
                st.session_state[f"{pillar}_{field}"] = DEFAULT_VALUES.get(pillar, {}).get(field, "")
        st.experimental_rerun()

    if st.button("Generate Report"):
        with st.spinner("Generating report..."):
            try:
                docs = st.session_state.agent.search_documentation("EKS best practices")
                risk_fig = st.session_state.agent.generate_risk_metrics()
                st.plotly_chart(risk_fig)
                
                pdf_file = st.session_state.agent.generate_report(inputs)
                
                if pdf_file:
                    with open(pdf_file, "rb") as file:
                        st.download_button(
                            label="Download Report",
                            data=file,
                            file_name="eks_review_report.pdf",
                            mime="application/pdf"
                        )
                
                if docs:
                    st.subheader("Relevant Documentation")
                    for doc in docs:
                        if isinstance(doc, dict) and 'title' in doc and 'url' in doc:
                            st.write(f"- [{doc['title']}]({doc['url']})")
                        else:
                            st.write(f"- {str(doc)}")
                
            except Exception as e:
                st.error(f"Error generating report: {str(e)}")
                logging.error(f"Error in report generation: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()
