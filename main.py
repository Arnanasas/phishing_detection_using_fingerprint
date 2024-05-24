from selenium_renderer import SeleniumRenderer
from database import PostgreSQLDatabase
from tlp_calculator import TLP_calculator
import configparser
# Example usage
if __name__ == "__main__":

    phish_urls = [
        'https://facebook.com/login'
    ]

    train_urls = ["http://www.conceptdraw.com/How-To-Guide/Local-Area-Network", "https://www.edrawsoft.com/Local-Area-Network.php", "http://www.webopedia.com/TERM/L/local_area_network_LAN.html", "https://www.acsac.org/secshelf/book001/16.pdf", "http://www.diffen.com/difference/LAN_vs_WAN", "http://sentence.yourdictionary.com/lan", "http://www.itrelease.com/2012/12/examples-and-types-of-networks/", "http://www.dictionary.com/browse/lan", "http://fcit.usf.edu/Network/chap1/chap1.htm", "http://www.Cisco.com/c/en/us/support/wireless/2100-series-wireless-lan-controllers/products-configuration-examples-list.html", "http://support.dlink.com/emulators/dcw725/RgConnect.html", "http://www.maxis.com.my/content/dam/maxis/en/personal/support/faq-images/devices/all-internet-devices/fibre/user-manual/fiber%20internet-%20MB%20TG784%20User%20Manual.pdf", "http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.178.31&rep=rep1&type=pdf", "http://www.Cisco.com/c/dam/en/us/td/docs/video/at_home/Cable_Modems/3800_Series/4021196_C.pdf", "https://en.wikipedia.org/wiki/Residential_gateway", "http://setuprouter.com/router/smartrg/sr500n/manual-1242.pdf", "http://ui.linksys.com/BEFCMUH4/twc/", "http://www.karistelefon.fi/sv/component/docman/doc_download/204-znid-24xx-configuration-guide", "https://www.speedguide.net/images/hardware/siemens/speedstream6500_manual.pdf",
                  "https://help.ting.com/hc/en-us/articles/206296637-Configuring-Your-Residential-Gateway-GigaCenter-844G-", "https://www.linkedin.com/jobs/", "https://www.linkedin.com/jobs/linkedin-jobs", "https://www.linkedin.com/jobs/view-all", "https://www.linkedin.com/jobs/directory/", "https://www.glassdoor.com/Jobs/LinkedIn-Jobs-E34865.htm", "https://twitter.com/linkedin_jobs", "http://jobs.jobvite.com/linkedin/jobs", "http://www.job-interview-site.com/linkedin-jobs-search-finding-jobs-using-linkedin.html", "https://play.google.com/store/apps/details?id=com.linkedin.android.jobs.jobseeker", "http://expandedramblings.com/index.php/linkedin-job-statistics/", "http://www.sawa.com/members/interactive-television-pvt-ltd", "http://ph.brainreactions.net/phone/33/22837144", "https://www.facebook.com/Interactive-Television-Pvt-Ltd-Group-M-100230523435650/photos/?ref=page_internal", "http://www.imepl.com/", "http://www.indiabook.com/cgi-bin/links/error.cgi?id=1588&title=Compuwave%20Interactive%20Television%20Pvt.%20Ltd.v", "http://tvfplay.com/", "https://www.linkedin.com/company/star-india-pvt-ltd", "https://en.wikipedia.org/wiki/Turner_International_India", "http://jobbuzz.timesjobs.com/review/company/38010", "https://www.redbooks.com/ad_agency/INTERACTIVE_AVENUES_PRIVATE_LIMITED/"]
    # Initialize the ConfigParser
    config = configparser.ConfigParser()
    config.read('config.ini')
    # Retrieve the DSN string directly
    dsn = config.get('database', 'dsn')

    # Render and save url's
    db = PostgreSQLDatabase(dsn)
    with db:
        # db.create_tables()
        renderer = SeleniumRenderer()
        renderer.render_and_save_url(train_urls)
        # calculator = TLP_calculator()
        # calculator.process_urls(legit_urls)
