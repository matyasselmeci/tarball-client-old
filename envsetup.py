'''Module to write the template setup.sh and setup.csh files

This is scripted because the contents of the setup files depend on the dver and
the basearch of the tarball they will be part of.

We need to write both a setup.csh.in and a setup.sh.in, and aside from the
syntax, their contents will be identical. With the shell_construct hash, we
get rid of a lot of the duplication.

shell_construct is a hash of hashes. The first key is the shell family, and the
second key identifies a shell construct -- a statement or fragment of a
statement. For example, the 'setenv' construct is to set an environment
variable.  In csh, it expands to 'setenv var "value"', and in sh, it expands to
'export var="value"'.  Each sub-hash must have the same keys.
Constructs that have arguments are lambdas; those that do not are strings.
'''

import os
import sys

def write_to_file(dest_path, text_to_write):
    dest_fh = open(dest_path, 'w')
    try:
        dest_fh.write(text_to_write)
    finally:
        dest_fh.close()


shell_construct = {
    'csh': {
        'setenv'     : (lambda var,value : 'setenv %s "%s"\n' % (var,value)),
        'unsetenv'   : (lambda var       : 'unsetenv %s\n' % var),
        'ifdef'      : (lambda var       : 'if ($?%s) then\n' % var),
        'ifreadable' : (lambda fname     : 'if -r "%s" then\n' % fname),
        'else'       : 'else\n',
        'endif'      : 'endif\n',
        'source'     : (lambda fname     : 'source "%s"\n' % (fname)),
    },
    'sh': {
        'setenv'     : (lambda var,value : 'export %s="%s"\n' % (var,value)),
        'unsetenv'   : (lambda var       : 'unset %s\n' % var),
        'ifdef'      : (lambda var       : 'if [ "X" != "X${%s-}" ]; then\n' % var),
        'ifreadable' : (lambda fname     : 'if [ -r "%s" ]; then\n' % fname),
        'else'       : 'else\n',
        'endif'      : 'fi\n',
        'source'     : (lambda fname     : '. "%s"\n' % (fname)),
    }
}



def write_setup_in_files(dest_dir, dver, basearch):
    '''Writes dest_dir/setup.csh.in and dest_dir/setup.sh.in according to the
    dver and basearch provided.

    '''
    for sh in 'csh', 'sh':
        dest_path = os.path.join(dest_dir, 'setup.%s.in' % sh)
        text_to_write = "# Source this file if using %s or a shell derived from it\n" % sh
        setup_local = "$OSG_LOCATION/setup-local.%s" % sh

        _setenv     = shell_construct[sh]['setenv']
        _unsetenv   = shell_construct[sh]['unsetenv']
        _ifdef      = shell_construct[sh]['ifdef']
        _else       = shell_construct[sh]['else']
        _endif      = shell_construct[sh]['endif']
        _ifreadable = shell_construct[sh]['ifreadable']
        _source     = shell_construct[sh]['source']

        text_to_write += (
              _setenv("OSG_LOCATION",     "@@OSG_LOCATION@@")
            + _setenv("GLOBUS_LOCATION",  "$OSG_LOCATION/usr")
            + _setenv("PATH",             "$OSG_LOCATION/usr/bin:$OSG_LOCATION/usr/sbin:$PATH")
            + "\n")

        if 'x86_64' == basearch:
            text_to_write += _setenv("OSG_LD_LIBRARY_PATH", "$OSG_LOCATION/usr/lib64:$OSG_LOCATION/usr/lib:$OSG_LOCATION/usr/lib64/dcap:$OSG_LOCATION/usr/lib64/lcgdm")
        else:
            text_to_write += _setenv("OSG_LD_LIBRARY_PATH", "$OSG_LOCATION/usr/lib:$OSG_LOCATION/usr/lib/dcap:$OSG_LOCATION/usr/lib/lcgdm")

        text_to_write += (
              _ifdef("LD_LIBRARY_PATH")
            + "\t" + _setenv("LD_LIBRARY_PATH", "${OSG_LD_LIBRARY_PATH}:$LD_LIBRARY_PATH")
            + _else
            + "\t" + _setenv("LD_LIBRARY_PATH", "${OSG_LD_LIBRARY_PATH}")
            + _endif
            + _unsetenv("OSG_LD_LIBRARY_PATH")
            + "\n")

        if 'el6' == dver:
            text_to_write += _setenv("OSG_PERL5LIB", "$OSG_LOCATION/usr/share/perl5/vendor_perl:$OSG_LOCATION/usr/share/perl5")
        else:
            text_to_write += _setenv("OSG_PERL5LIB", "$OSG_LOCATION/usr/lib/perl5/vendor_perl/5.8.8")

        text_to_write += (
              _ifdef("PERL5LIB")
            + "\t" + _setenv("PERL5LIB", "${OSG_PERL5LIB}:$PERL5LIB")
            + _else
            + "\t" + _setenv("PERL5LIB", "${OSG_PERL5LIB}")
            + _endif
            + _unsetenv("OSG_PERL5LIB")
            + "\n")

        # Arch-independent python stuff always goes in usr/lib/, even on x86_64
        if 'el6' == dver:
            osg_pythonpath = "$OSG_LOCATION/usr/lib/python2.6/site-packages"
            if 'x86_64' == basearch:
                osg_pythonpath += ":$OSG_LOCATION/usr/lib64/python2.6/site-packages"
        else:
            osg_pythonpath = "$OSG_LOCATION/usr/lib/python2.4/site-packages"
            if 'x86_64' == basearch:
                osg_pythonpath += ":$OSG_LOCATION/usr/lib64/python2.4/site-packages"
        text_to_write += _setenv("OSG_PYTHONPATH", osg_pythonpath)

        text_to_write += (
              _ifdef("PYTHONPATH")
            + "\t" + _setenv("PYTHONPATH", "${OSG_PYTHONPATH}:$PYTHONPATH")
            + _else
            + "\t" + _setenv("PYTHONPATH", "${OSG_PYTHONPATH}")
            + _endif
            + _unsetenv("OSG_PYTHONPATH")
            + "\n")

        text_to_write += (
              _setenv("X509_CERT_DIR", "$OSG_LOCATION/etc/grid-security/certificates")
            + _setenv("X509_VOMS_DIR", "$OSG_LOCATION/etc/grid-security/vomsdir")
            + _setenv("VOMS_USERCONF", "$OSG_LOCATION/etc/vomses"))

        text_to_write += (
              _ifdef("MANPATH")
            + "\t" + _setenv("MANPATH", "$OSG_LOCATION/usr/share/man:$MANPATH")
            + _else
            + "\t" + _setenv("MANPATH", "$OSG_LOCATION/usr/share/man")
            + _endif
            + "\n")

        text_to_write += (
              "\n"
            + "# Site-specific customizations\n"
            + _ifreadable(setup_local)
            + "\t" + _source(setup_local)
            + _endif
            + "\n")

        write_to_file(dest_path, text_to_write)


def main(argv):
    dest_dir, dver, basearch = argv[1:4]
    write_setup_in_files(dest_dir, dver, basearch)

if __name__ == '__main__':
    sys.exit(main(sys.argv))

