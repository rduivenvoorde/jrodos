
def path_to_dirname(self, project, path, timestamp):
    # path.split('=;=')[-2]+'_'+path.split('=;=')[-1]
    dirname = tempfile.gettempdir() + os.sep
    dirname += self.slugify(unicode(project)) + '_'
    dirname += self.slugify(unicode(path.split('=;=')[-2])) + '_'
    dirname += self.slugify(unicode(path.split('=;=')[-1])) + '_'
    dirname += timestamp
    if not os.path.exists(dirname):
        os.mkdir(dirname)
    # else:
    #    raise Exception("Directory already there????")
    return dirname


def slugify(self, value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    import unicodedata, re
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = unicode(re.sub('[^\w\s-]', '', value).strip())
    value = unicode(re.sub('[-\s]+', '-', value))
    return value