from dataclasses import replace


class CampaignService:
    def _init_(self):
        self.campaigns = {}

    def add_campaign(self, campaign):
        if campaign.campaign_id in self.campaigns:
            raise ValueError("Campaign already exists")

        self.campaigns[campaign.campaign_id] = campaign
        return campaign

    def get_campaign(self, campaign_id):
        if campaign_id not in self.campaigns:
            raise ValueError("Campaign not found")

        return self.campaigns[campaign_id]

    def get_all_campaigns(self):
        return list(self.campaigns.values())

    def update_campaign(self, campaign_id, **updates):
        campaign = self.get_campaign(campaign_id)
        updated_campaign = replace(campaign, **updates)
        self.campaigns[campaign_id] = updated_campaign
        return updated_campaign

    def delete_campaign(self, campaign_id):
        self.get_campaign(campaign_id)
        del self.campaigns[campaign_id]
        return True

    def get_active_campaigns(self, current_date):
        return [
            campaign
            for campaign in self.campaigns.values()
            if campaign.flight_start <= current_date <= campaign.flight_end
        ]