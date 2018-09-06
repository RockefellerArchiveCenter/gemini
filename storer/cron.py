from django_cron import CronJobBase, Schedule

from storer.routines import AIPStoreRoutine, DIP


class StorePackage(CronJobBase):
    RUN_EVERY_MINS = 1
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)

    def do(self):
        if self.package_type == 'AIP':
            AIPStoreRoutine.run()
        elif self.package_type == 'DIP':
            DIPStoreRoutine.run()


class StoreAIPs(StorePackage):
    package_type = 'AIP'
    code = 'storer.store_aips'


class StoreAIPs(StorePackage):
    package_type = 'DIP'
    code = 'storer.store_dips'
