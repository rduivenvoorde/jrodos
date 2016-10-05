import os.path, tempfile

class Utils:

    @staticmethod
    def jrodos_dirname(project, path, timestamp):
        # path.split('=;=')[-2]+'_'+path.split('=;=')[-1]
        dirname = tempfile.gettempdir() + os.sep + timestamp + '_'
        dirname += Utils.slugify(unicode(project)) + '_'
        if len(path.split('=;=')) >= 2:
            dirname += Utils.slugify(unicode(path.split('=;=')[-2])) + '_'
            dirname += Utils.slugify(unicode(path.split('=;=')[-1]))

        if not os.path.exists(dirname):
            os.mkdir(dirname)
        # else:
        #    raise Exception("Directory already there????")
        return dirname

    @staticmethod
    def slugify(value):
        """
        Normalizes string, converts to lowercase, removes non-alpha characters,
        and converts spaces to hyphens.
        """
        import unicodedata, re
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
        value = unicode(re.sub('[^\w\s-]', '', value).strip())
        value = unicode(re.sub('[-\s]+', '-', value))
        return value

if __name__ == '__main__':

    from datetime import datetime
    print(Utils.jrodos_dirname('test', 'test', datetime.now().strftime("%Y%m%d%H%M%S")))
    print(Utils.jrodos_dirname('test', 'test0=;=test1', datetime.now().strftime("%Y%m%d%H%M%S")))
    print(Utils.jrodos_dirname('test', 'test0=;=test1=;=test2', datetime.now().strftime("%Y%m%d%H%M%S")))

    Utils.set_settings_value("rivmtest", "test2")
    print(Utils.get_settings_value("rivmtest", "test_default"))
