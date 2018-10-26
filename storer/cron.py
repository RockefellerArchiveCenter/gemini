from django_cron import CronJobBase, Schedule

from storer.routines import AIPStoreRoutine, DIPStoreRoutine


class StorePackage(CronJobBase):
    RUN_EVERY_MINS = 1
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)

    def do(self, dirs=None):
        if self.package_type == 'AIP':
            AIPStoreRoutine(dirs).run()
        elif self.package_type == 'DIP':
            DIPStoreRoutine(dirs).run()
        else:
            AIPStoreRoutine(dirs).run()
            DIPStoreRoutine(dirs).run()


class StoreAIPs(StorePackage):
    package_type = 'AIP'
    code = 'storer.store_aips'


class StoreDIPs(StorePackage):
    package_type = 'DIP'
    code = 'storer.store_dips'
